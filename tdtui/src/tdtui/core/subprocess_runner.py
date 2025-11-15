import subprocess


def run_bash(command: str):
    cmd = command.split(" ")
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,  # <<< key bit
    )

    for line in p.stdout:
        print(line, end="")  # already a str, prints cleanly

    p.stdout.close()
    p.wait()
