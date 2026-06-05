# 011. Pod Security Hardening

Date: 2026-06-05
Status: Accepted

## Context

Running containerized workloads on Kubernetes (EKS) requires defense-in-depth security measures to protect the host node and other workloads from potential container breakout vulnerabilities. By default, containers run with root privileges and have a read-write root filesystem, which increases the blast radius if the application is compromised.

To comply with the Verdict platform security defaults (specifically Section 3 and Section 9 of `agent.md`), we must harden the pod and container runtimes.

## Decision

We will explicitly configure and enforce the following security context settings directly in `helm/verdict-app/templates/deployment.yaml`:

1. **Pod-level Security Context:**
   - `runAsNonRoot: true`: Enforces that the container must run as a non-root user. If the image attempts to run as UID 0 (root), kubelet will fail to start it.
   - `runAsUser: 10001`: Configures the container processes to execute with UID 10001 (matching the `appuser` defined in the Dockerfile).
   - `fsGroup: 10001`: Configures the volume ownership of mounted volumes to GID 10001, allowing the non-root user to read/write mounted volumes.

2. **Container-level Security Context:**
   - `allowPrivilegeEscalation: false`: Prevents a process from gaining more privileges than its parent process (e.g. via `setuid` or `setgid` binaries).
   - `readOnlyRootFilesystem: true`: Mounts the container's root filesystem as read-only. This prevents attackers from writing malicious binaries, scripts, or configuration files directly to the container filesystem.
   - `capabilities.drop: ["ALL"]`: Drops all Linux capabilities (privileges) from the container processes. Standard workloads rarely need any of the default Linux capabilities.
   - `seccompProfile.type: RuntimeDefault`: Enforces the default seccomp profile provided by the container runtime (e.g. containerd), which restricts standard Linux system calls.

3. **Ephemeral Writes Support:**
   - Because the root filesystem is read-only, Uvicorn and FastAPI cannot write temporary files or pid files to standard paths. We mount an `emptyDir` volume at `/tmp` so the application can perform temporary write operations successfully.

## Consequences

- **Hardened Workload:** If the FastAPI application is compromised, the attacker cannot modify files on the root filesystem, escalate privileges to root, or execute restricted system calls.
- **Application Compatibility:** The application must only write to the mounted `/tmp` directory. Writing to any other directory will fail with a `Read-only file system` error. The `detect_changed_tests.py` script and `run_tests.py` scripts must write outputs to `/tmp` if executed inside the container.
- **Enforced Security Policy:** Enforcing this directly in the deployment template (rather than solely relying on `values.yaml` defaults) ensures the security policy cannot be accidentally bypassed by overriding or omitting the values variables.

## Cost Impact

- **$0.** Enforcing security context parameters has no impact on AWS resource billing or consumption.
