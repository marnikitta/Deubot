# GitHub Actions Deployment Setup

This document explains how to configure GitHub secrets for automated deployment.

## Required GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions, and add the following secrets:

### 1. `DEPLOYMENT_SSH_USER`
The SSH username for the deployment server.
```
Example: marnikitta
```

### 2. `DEPLOYMENT_SSH_HOST`
The hostname or IP address of the deployment server.
```
Example: deubot.example.com
```

### 3. `DEPLOYMENT_SSH_KEY`
The private SSH key for authentication. Generate a dedicated deployment key:

```bash
# Generate a new SSH key pair (do NOT use your personal key)
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deubot_deploy

# Copy the PRIVATE key content to GitHub secrets
cat ~/.ssh/deubot_deploy

# Copy the PUBLIC key to your server
ssh-copy-id -i ~/.ssh/deubot_deploy.pub user@your-server
```

**Important**: Never reuse your personal SSH key for automation.

### 4. `DEPLOYMENT_SSH_HOST_KEY`
The server's SSH host key for security (prevents MITM attacks).

```bash
# Get the host key from your server
ssh-keyscan -p 2222 your-server-hostname

# Example output:
# [your-server]:2222 ssh-rsa AAAAB3NzaC1yc2EAAAA...
# [your-server]:2222 ecdsa-sha2-nistp256 AAAAE2VjZHNh...
# [your-server]:2222 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA...
```

Copy all three lines (ssh-rsa, ecdsa, and ed25519) to this secret. Multiple lines are supported.

### 5. `DEPLOYMENT_SSH_PORT` (Optional)
The SSH port if different from 22.
```
Example: 2222
```
Leave empty if using the default port 22.

## Security Notes

✅ **What we do right:**
- Use dedicated deployment keys (not personal keys)
- Enable `StrictHostKeyChecking yes` to prevent MITM attacks
- Store host fingerprints to verify server identity
- Use GitHub secrets for sensitive data
- Set proper SSH key permissions (600)
- Use concurrency control to prevent simultaneous deployments

❌ **Never do this:**
- Set `StrictHostKeyChecking no` (security vulnerability!)
- Commit SSH keys to the repository
- Use personal SSH keys for automation
- Share deployment keys across projects

## Testing the Setup

After configuring secrets, push to main branch:

```bash
git add .github/
git commit -m "Add GitHub Actions deployment workflow"
git push origin main
```

Monitor the deployment in the Actions tab of your GitHub repository.

## Troubleshooting

### SSH Connection Fails
- Verify the public key is added to `~/.ssh/authorized_keys` on the server
- Check the SSH port is correct
- Ensure the user has permission to access the deployment directory

### Host Key Verification Failed
- Re-run `ssh-keyscan -H your-hostname` and update the `DEPLOYMENT_SSH_HOST_KEY` secret
- Make sure you're scanning the correct hostname (same as `DEPLOYMENT_SSH_HOST`)

### Deployment Succeeds But Service Doesn't Start
- SSH into the server and check logs: `journalctl --user-unit=deubot.service`
- Verify systemd service is installed: `systemctl --user status deubot.service`
