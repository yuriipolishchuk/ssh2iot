# Admin console for AWS IoT Secure Tunneling

import boto3
import argparse
import sys
import time
import socket
import subprocess

aws_regions = [
    "ap-northeast-1",
    "ap-northeast-2",
    "ap-south-1",
    "ap-southeast-1",
    "ap-southeast-2",
    "ca-central-1",
    "eu-central-1",
    "eu-north-1",
    "eu-west-1",
    "eu-west-2",
    "eu-west-3",
    "sa-east-1",
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
]

parser = argparse.ArgumentParser(description="Connect to IoT thing behind firewall via SSH over AWS IoT Secure Tunneling.")

parser.add_argument('-i', '--thing-name', required=True, help="IoT thing name")
parser.add_argument('-t', '--timeout', default=720, type=int,
                    help="The maximum time in minutes a tunnel can remain open")
parser.add_argument('-s', '--service', default="ssh", choices=['ssh', 'scp'], help="Service to use")
parser.add_argument('-r', '--region', default="us-east-1", choices=aws_regions, help="Service to use")
parser.add_argument('-u', '--ssh-user', default="root", help="SSH user, default 'root'")


args = parser.parse_args()


def open_tunnel(thing_name, service, timeout):
    try:
        response = client.open_tunnel(
            description='tunnel to {}'.format(thing_name),
            tags=[
                {
                    'key': 'thing',
                    'value': thing_name
                },
            ],
            destinationConfig={
                'thingName': thing_name,
                'services': [
                    service,
                ]
            },
            timeoutConfig={
                'maxLifetimeTimeoutMinutes': timeout
            }
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            tunnel_id = response["tunnelId"]
            token = response["sourceAccessToken"]
            print("Secure tunnel {} has been opened. Expires in {} minutes ".format(tunnel_id, args.timeout))
            return tunnel_id, token

    except Exception as e:
        print(str(e))
        sys.exit(-1)


def wait_for_iot_device_connected(tunnel_id, thing_name):
    print("Waiting for IoT device {} to connect...".format(thing_name))
    attempt = 1
    while attempt < 30:
        time.sleep(2)
        try:
            response = client.describe_tunnel(tunnelId=tunnel_id)
            if response["tunnel"]["status"] == "CLOSED":
                print("Tunnel was closed. Exiting...")
                sys.exit(-1)
            if response["tunnel"]["destinationConnectionState"]["status"] == "CONNECTED":
                print("IoT thing '{}' connected to tunnel.".format(thing_name))
                return
        except Exception as e:
            print(str(e))

        attempt += 1

    print("IoT device couldn't connect to tunnel")
    sys.exit(-1)


def wait_for_source_device_connected(tunnel_id):
    print("Waiting for localproxy to connect to tunnel...")
    attempt = 1
    while attempt < 30:
        time.sleep(2)
        try:
            response = client.describe_tunnel(tunnelId=tunnel_id)
            if response["tunnel"]["status"] == "CLOSED":
                print("Tunnel was closed. Exiting...")
                sys.exit(-1)
            if response["tunnel"]["sourceConnectionState"]["status"] == "CONNECTED":
                print("localproxy connected to tunnel.")
                return
        except Exception as e:
            print(str(e))

        attempt += 1

    print("IoT device couldn't connect to tunnel")
    sys.exit(-1)




def get_random_unused_tcp_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    addr = s.getsockname()
    s.close()
    return addr[1]


# launch localproxy in source mode
def run_localproxy(token, region=args.region):
    port = get_random_unused_tcp_port()

    try:

        proc = subprocess.Popen(
            [
                '/usr/local/bin/localproxy',
                '-r', region,
                '-s', str(port)
            ],
            env={"AWSIOT_TUNNEL_ACCESS_TOKEN": token},
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        print("localproxy started, pid: {}".format(proc.pid))
        return proc, port

    except Exception as e:
        print("Cannot start localproxy")
        print(str(e))


if __name__ == '__main__':
    client = boto3.client('iotsecuretunneling', region_name=args.region)

    thing_name = args.thing_name

    # open secure tunnel
    tunnel_id, token = open_tunnel(thing_name, args.service, args.timeout)

    wait_for_iot_device_connected(tunnel_id, thing_name)

    # run localproxy
    proxy_proc, port = run_localproxy(token)
    wait_for_source_device_connected(tunnel_id)

    # ssh to iot thing through tunnel
    try:
        retcode = subprocess.call("ssh -o 'StrictHostKeyChecking no' {}@127.0.0.1 -p {}".format(args.ssh_user, port), shell=True)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)

    # stop localproxy
    proxy_proc.terminate()

    # close and delete tunnel
    response = client.close_tunnel(tunnelId=tunnel_id, delete=True)
    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        print("Tunnel {} closed and deleted.".format(tunnel_id))
