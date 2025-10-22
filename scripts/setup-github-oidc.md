# GitHub OIDC Setup Guide

This guide explains how to set up secure OIDC authentication between GitHub Actions and AWS, eliminating the need to store AWS access keys in GitHub secrets.

## What is OIDC Authentication?

OpenID Connect (OIDC) allows GitHub Actions to authenticate with AWS using short-lived tokens instead of long-lived access keys. This is more secure because:

- No AWS credentials stored in GitHub
- Tokens are automatically rotated
- Access is scoped to specific repositories and branches
- Follows AWS security best practices

## Setup Steps

### 1. Deploy Infrastructure with OIDC Support

The Terraform configuration includes OIDC setup automatically:

```bash
cd terraform
terraform apply
```

This creates:
- GitHub OIDC Identity Provider
- IAM Role for GitHub Actions
- Proper trust policies and permissions

### 2. Get the Role ARN

After Terraform deployment, get the GitHub Actions role ARN:

```bash
cd terraform
terraform output github_actions_role_arn
```

Copy this ARN - you'll need it for GitHub secrets.

### 3. Configure GitHub Repository Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add these secrets:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/agentleague-github-actions-role` | The role ARN from Terraform output |
| `DOMAIN_NAME` | `dev.yourdomain.com` | Your application domain |

### 4. Verify Configuration

The GitHub Actions workflow will now:

1. Request a JWT token from GitHub's OIDC provider
2. Exchange it for AWS credentials using the IAM role
3. Use temporary credentials for AWS operations

### 5. Test the Setup

Push a commit to the main branch or manually trigger the workflow:

```bash
git add .
git commit -m "Test OIDC authentication"
git push origin main
```

Check the Actions tab to see if authentication works.

## Security Benefits

✅ **No long-lived credentials**: AWS access keys never stored in GitHub
✅ **Automatic rotation**: Tokens expire automatically
✅ **Repository scoped**: Only your specific repository can assume the role
✅ **Branch restrictions**: Can be limited to specific branches
✅ **Audit trail**: All actions logged in AWS CloudTrail

## Troubleshooting

### Common Issues

1. **"No OpenIDConnect provider found"**
   - Ensure Terraform applied successfully
   - Check if OIDC provider exists in AWS IAM console

2. **"Not authorized to perform sts:AssumeRoleWithWebIdentity"**
   - Verify the role ARN in GitHub secrets
   - Check the trust policy allows your repository

3. **"Invalid identity token"**
   - Ensure `permissions: id-token: write` is set in workflow
   - Check repository name matches the trust policy

### Verification Commands

```bash
# Check if OIDC provider exists
aws iam list-open-id-connect-providers

# Check role trust policy
aws iam get-role --role-name agentleague-github-actions-role

# View role permissions
aws iam list-attached-role-policies --role-name agentleague-github-actions-role
```

## Advanced Configuration

### Restrict to Specific Branches

To limit access to only the `main` branch, update the trust policy condition:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:ref:refs/heads/main"
  }
}
```

### Add Environment Restrictions

For production deployments, you can restrict to specific GitHub environments:

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": "repo:your-org/your-repo:environment:production"
  }
}
```

## Migration from Access Keys

If you're migrating from stored AWS access keys:

1. Deploy the OIDC configuration
2. Update GitHub secrets (remove old keys, add role ARN)
3. Test the workflow
4. Delete the old IAM user/access keys

## Resources

- [AWS IAM OIDC Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- [GitHub OIDC Documentation](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
- [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
