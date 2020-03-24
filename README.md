
# Reverse SSH Project

## Task

```
The goal of the project is to provide SSH access (console and/or file operations) to a device running
a linux instance on demand, from arbitrary locations. The device is typically hidden behind a
firewall/home router and has internet access. The admin console may be located anywhere and also has
internet access.

To provide SSH access to the device, we can use reverse SSH. The way this works is the following:
- The device performs an SSH connection to a pivot server, setting up a reverse port forwarding from a
pivot port to local SSH port 22 (using parameter -R)
- The admin console opens an SSH connection to the pivot server and connects to the camera using SSH via
the pivot port

We can have millions of devices online but only a few (less than 10) will require SSH access
simultaneously, so having continuous SSH access for all devices is not desirable. We therefore assume
that a device is going to use AWS IoT to subscribe to a topic and wait for incoming requests.
Once a request is received, the device will then initiate a reverse connection to the pivot server. The
pivot server to connect to (address/port) will be provided in the IoT message. The reverse SSH
connection will remain active until the incoming SSH connection is terminated.

For security purposes, we assume that access to devices is controlled by SSH permission to access the
pivot server by the admin console, i.e. if an admin console is allowed to SSH into the pivot server we
assume that they will also have permission to access devices. Also, all SSH connections will use public
key auth, not passwords.

Ease of use is required. Each device will have a unique id and the admin console will only need to know
this id (and "static" info such as the pivot server address and SSH credentials to connect). The system
will also provide intelligible messages in case the device is offline.

Deliverables:
- a terraform script that will setup the pivot server and IoT devices on AWS (at a particular region)
- pivot server code and configuration needed for supporting the reverse SSH scenario
- device code and configuration for subscribing to the IoT topic and triggering the SSH connection (and
terminating the connection)
- admin console code for requesting the reverse SSH connection and opening the SSH connection to the
device, for SSH and for SCP
- a demo with starting one or two devices and then performing the SSH connection from an admin console

Recommendations:
- Python is recommended but any other language is also acceptable
- each device should be a docker container running a typical linux distro (ubuntu, fedora, arch), with no
port forwardings but with internet access
- admin console may also be a separate docker container (it will eventually be used from a regular
mac/linux prompt)

It is also possible for alternative solutions to be proposed, the goal is to provide SSH access to devices
behind firewalls easily and reliably.
```

---

## Deployment instructions for demo:

* Bootstrap requirements for terraform (s3 bucket + dynamodb table):

```bash
cd terraform/bootstrap
terraform init && terraform apply
```

* Provision IoT infra with terraform:

```bash
cd ../environments/test
terraform init && terraform apply
```

* Configure IoT things (get endpoint and certs from terraform output):

```bash
terraform output -json this | jq -r '.certificate.certificate_pem' > ../../../certs/certificate.pem.crt
terraform output -json this | jq -r '.certificate.private_key' > ../../../certs/private.pem.key

ENDPOINT=$(terraform output -json this | jq -r '.endpoint')
grep ENDPOINT ../../../things.env || echo "ENDPOINT=${ENDPOINT}" >> ../../../things.env
```

* Run IoT things (with tunnel agent and local proxy):

```bash
docker-compose up --build
```

* Add your public key to `authorized_keys`:

```bash
cat ~/.ssh/id_rsa.pub >> authorized_keys
```

or get if from GitHub with:

```bash
wget -O authorized_keys https://github.com/yuriipolishchuk.keys
```

replacing `yuriipolishchuk` with your github username.


* Create alias for SSH wrapper

```bash
alias ssh2iot "docker run --rm -it -v $HOME/.aws:/root/.aws -v $HOME/.ssh:/root/.ssh -e AWS_PROFILE=$AWS_PROFILE ssh2iot:latest"

# or pass AWS credentials as environment variables
alias ssh2iot "docker run --rm -it  -v $HOME/.ssh:/root/.ssh -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY -e AWS_PROFILE=$AWS_PROFILE ssh2iot:latest"
```

* Run SSH wrapper to connect to IoT things over AWS IoT Secure Tunnel

```bash
ssh2iot  -i MyIotThing1 -r eu-west-1
```

To connect to another thing just change `-i` parameter to `MyIotThing2`

To reuse existing tunnel (for cost reduction):

```bash
ssh2iot -i MyIotThing1 -r eu-west-1 --tunnel $TUNNEL --token $TOKEN
```

For `$TUNNEL` and `$TOKEN` values see the output of the command in which tunnel was opened.

NOTE: IAM roles can be used for AuthN/Z if container is running on EC2 instance.

---

## TODO:

* Implement file copy mode for `scp`

* Re-architect to use pivot server for cost savings.

* Alternatively websockets proxy can be considered. For example [wstunnel](https://github.com/mhzed/wstunnel):

  ```bash
  ssh -o ProxyCommand="wstunnel -c -t stdio:%h:%p https://server" user@sshDestination
  ```

  websocket server implementation must handle AuthN/Z and keep tunnels state

* Restrict permissions for IoT devices in IAM policy

* Use separate certificates for devices

* Implement async stdio both for agent and ssh wrapper

* Fix defunct subprocesses aka zombies

* Make use of classes (OOP)

* Cover the code with unit/integration tests

* Comment the code properly

* Implement sending notifications for IoT device from admin console (SSH wrapper) on tunnel creation.
  This will resolve issue when IoT thing was launched after tunnel creation, so it doesn't have token.

As temporary workaround you can send the token to IoT thing from `AWS IoT Core console (UI) -> Test -> Publish`
use topic `$aws/things/MyIotThing1/tunnels/notify`, where `MyIotThing1` is a thing name,
and payload:

```json
{
  "clientAccessToken": "AQGAA...",
  "clientMode": "destination",
  "region": "eu-west-1",
  "services": [
    "ssh"
  ]
}
```

`clientAccessToken` value is in output of the command in which tunnel was opened.

---


## CLEANUP:

* Clean docker-compose containers, volumes and images

```bash
docker-compose down --volumes --rmi all --remove-orphans
```

* Destroy terraform infrastructure

```bash
cd terraform/environments/test
terraform destroy

cd ../../bootstrap
terraform destroy
```
