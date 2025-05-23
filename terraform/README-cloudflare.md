# Cloudflare Custom Domain Setup

This document explains how to configure a custom domain using Cloudflare for your frontend CloudFront distribution.

## Prerequisites

1. A domain managed by Cloudflare
2. Cloudflare account email and Global API Key
3. Your Cloudflare Zone ID

## Setup Instructions

### 1. Get Your Cloudflare Global API Key

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/profile/api-tokens)
2. Scroll down to the "API Keys" section
3. Click "View" next to "Global API Key"
4. Enter your password to reveal the key
5. Copy the Global API Key

### 2. Get Your Zone ID

1. In your Cloudflare dashboard, select your domain
2. In the right sidebar, you'll see your "Zone ID"
3. Copy this value

### 3. Configure Terraform Variables

Create a `terraform.tfvars` file (copy from `terraform.tfvars.example`):

```hcl
# Cloudflare Configuration
cloudflare_email = "your-cloudflare-email@example.com"
cloudflare_api_key = "your-cloudflare-global-api-key"
cloudflare_zone_id = "your-actual-zone-id-here" 
cloudflare_domain_name = "yourdomain.com"
cloudflare_subdomain = "cc"
```

### 4. Initialize and Apply

```bash
# Initialize Terraform (if Cloudflare provider is new)
terraform init

# Plan the changes
terraform plan

# Apply the changes
terraform apply
```

## What This Creates

The configuration will create:

1. **CNAME Record**: `cc.yourdomain.com` → CloudFront distribution domain
2. **DNS Resolution**: Your subdomain will resolve to the CloudFront distribution
3. **HTTPS**: Automatic HTTPS via CloudFront (using CloudFront's default certificate)

## Important Notes

### SSL/TLS Certificates

The current setup uses CloudFront's default SSL certificate. For a custom domain in production, you should:

1. **Option 1**: Request an SSL certificate from AWS Certificate Manager (ACM) in `us-east-1` region
2. **Option 2**: Use Cloudflare's SSL/TLS settings (if `proxied = true`)

### Cloudflare Proxy Settings

The configuration sets `proxied = false` by default. You can change this to `true` if you want:
- Cloudflare's CDN/caching
- Cloudflare's security features
- Cloudflare's SSL certificate

### DNS Propagation

After applying, DNS changes may take a few minutes to propagate globally.

## Troubleshooting

### Common Issues

1. **Invalid Credentials**: Ensure your email and Global API Key are correct
2. **Zone ID Mismatch**: Verify your Zone ID matches your domain
3. **DNS Not Resolving**: Wait for DNS propagation (up to 24 hours, usually 5-10 minutes)

### Verification Commands

```bash
# Check DNS resolution
nslookup cc.yourdomain.com

# Check HTTPS access
curl -I https://cc.yourdomain.com

# View Terraform outputs
terraform output
```

## Environment Variables Alternative

Instead of using `terraform.tfvars`, you can set environment variables:

```bash
export TF_VAR_cloudflare_email="your-cloudflare-email@example.com"
export TF_VAR_cloudflare_api_key="your-cloudflare-global-api-key"
export TF_VAR_cloudflare_zone_id="your-zone-id"
export TF_VAR_cloudflare_domain_name="yourdomain.com"
export TF_VAR_cloudflare_subdomain="cc"
```

## Security Best Practices

1. **Never commit** your `terraform.tfvars` file to version control
2. **Protect your Global API Key** as it has full account access
3. **Rotate API keys** regularly
4. **Consider using** scoped API tokens instead of Global API Key for production
5. **Consider using** Terraform Cloud or other secure secret management for production 