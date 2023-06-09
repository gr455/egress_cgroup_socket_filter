import attach
import docker
import click
import json
from bcc import BPF

def log(level, message, color):
	click.echo(click.style(f"{level}: {message}", fg=color))

def fatal(message):
	log("Fatal", message, "red")

def info(message):
	log("Info", message, "white")

@click.command()
@click.option("-i", type = str, help = "Pass container id")
@click.option("-n", type = str, help = "Pass container name")
@click.option("-d", is_flag = True, help = "Detach trace print from terminal")
@click.argument("action")
@click.argument("blacklistfile")
def cli(i, n, d, action, blacklistfile):
	if not action:
		fatal("No action passed")
	if action != "attach" and action != "detach":
		fatal("Illegal action")
	if not i:
		if not n:
			fatal("No args passed")
			return
		client = docker.from_env()
		container = None
		try:
			container = client.containers.get(n)
		except docker.errors.NotFound as e:
			fatal(f"No such container: {n}")
			return

		i = container.id

	# container id exists now
	cgroup2_path = "/sys/fs/cgroup/system.slice/" + "docker-" + i + ".scope"

	# create bcc bpf object
	b = attach.getBPF()
	
	disallowDict = {}

	# read blacklist file
	with open(blacklistfile, "r") as disallowFile:
		disallowDict = json.load(disallowFile)
	print(disallowDict)

	# set disallow bpf hash
	attach.setDisallowHash(b, disallowDict)
	# return
	# detach existing handlers
	info("Detatching existing handlers...")
	try:
		attach.sock(b, attach.DETACH)
	except Exception as e:
		info("No sock to detach")
	try:
		attach.kprobe(b, attach.DETACH)
	except Exception as e:
		info("No kprobe to detach")
		print(e)

	if action == "attach":
		info("Attaching handlers...")
		attach.kprobe(b)
		attach.sock(b, cgroup2_path)
		if not d:
			try:
				b.trace_print()
			except KeyboardInterrupt:
			 	info("Detatching...")
			 	attach.sock(b, cgroup2_path, attach.DETACH)
			 	attach.kprobe(b, attach.DETACH)


if __name__ == '__main__':
	cli()