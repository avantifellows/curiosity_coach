# Staging Environment Deployment Guide

This guide explains how to deploy and manage your staging environment using Terraform workspaces.

## Overview

Your infrastructure now supports two environments:
- **Production** (default workspace): Full infrastructure with dedicated RDS instance
- **Staging** (staging workspace): Separate infrastructure sharing the RDS instance from production

## Architecture

### Production Environment (`default` workspace)
- S3 Bucket: `curiosity-coach-frontend-dev`
- Backend Lambda: `curiosity-coach-backend-dev-lambda`
- Brain Lambda: `curiosity-coach-brain-lambda`
- RDS Instance: `curiosity-coach-backend-dev-rds`
- Domain: `curiosity.avantifellows.org`

### Staging Environment (`staging` workspace)
- S3 Bucket: `curiosity-coach-frontend-staging`
- Backend Lambda: `curiosity-coach-backend-staging-lambda`
- Brain Lambda: `curiosity-coach-brain-staging-lambda`
- RDS: **Shared** with production (separate database: `curiosity_coach_staging`)
- Domain: `curiosity-staging.avantifellows.org`

## Prerequisites

1. **Create Staging Database**: Connect to your RDS instance and create the staging database:
   ```sql
   -- Connect to your RDS instance using psql or any PostgreSQL client
   psql -h curiosity-coach-backend-dev-rds.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com -U dbadmin -d postgres
   
   -- Create staging database
   CREATE DATABASE curiosity_coach_staging;
   
   -- Verify it was created
   \l
   ```

2. **Update Configuration Files**: Ensure your application configuration files are ready for different environments.

## Deployment Commands

### Deploy Production Environment
```bash
# Ensure you're in the terraform directory
cd terraform

# Switch to production workspace
terraform workspace select default

# Plan the deployment
terraform plan -var-file="terraform.tfvars"

# Apply changes (if plan looks good)
terraform apply -var-file="terraform.tfvars"
```

### Deploy Staging Environment
```bash
# Switch to staging workspace
terraform workspace select staging

# Plan the deployment
terraform plan -var-file="terraform.staging.tfvars"

# Apply changes (if plan looks good)
terraform apply -var-file="terraform.staging.tfvars"
```

### Check Current Workspace
```bash
terraform workspace list
```

## Configuration Files

### `terraform.tfvars` (Production)
Contains production-specific variables including:
- `environment = "dev"`
- `cloudflare_subdomain = "curiosity"`
- `create_rds_instance = true` (implicit default)

### `terraform.staging.tfvars` (Staging)
Contains staging-specific variables including:
- `environment = "staging"`
- `cloudflare_subdomain = "curiosity-staging"`
- `create_rds_instance = false`
- `existing_rds_instance_id = "curiosity-coach-backend-dev-rds"`
- `existing_rds_password = "xT$PI}kL2CRwf2zb"`

## Key Differences in Staging

1. **Resource Naming**: All resources are suffixed with `-staging`
2. **Docker Tags**: Uses `staging` tag instead of `latest`
3. **Database**: Uses existing RDS instance but separate database
4. **Domain**: Different subdomain for staging
5. **S3 Buckets**: Separate buckets for frontend and brain config

## Environment Variables

The Lambda functions will automatically receive environment-specific variables:
- `DB_NAME`: `curiosity_coach_staging` for staging vs `curiosity_coach_dev` for production
- `FRONTEND_URL`: Points to staging CloudFront distribution
- `SQS_QUEUE_URL`: Staging-specific SQS queue

## Outputs

After deployment, you can check the outputs:
```bash
# For production
terraform workspace select default
terraform output

# For staging
terraform workspace select staging
terraform output
```

## Database Management

### Connect to Staging Database
```bash
# Using the shared RDS instance, connect to staging database
psql -h curiosity-coach-backend-dev-rds.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com -U dbadmin -d curiosity_coach_staging
```

### Migrate Data (if needed)
```bash
# Export from production database
pg_dump -h curiosity-coach-backend-dev-rds.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com -U dbadmin -d curiosity_coach_dev > prod_dump.sql

# Import to staging database (be careful with this!)
psql -h curiosity-coach-backend-dev-rds.ct2k2vwmh0ce.ap-south-1.rds.amazonaws.com -U dbadmin -d curiosity_coach_staging < prod_dump.sql
```

## CI/CD Pipeline Updates

Update your deployment scripts to handle both environments:

### Example Deploy Script
```bash
#!/bin/bash
ENVIRONMENT=$1

if [ "$ENVIRONMENT" = "staging" ]; then
    terraform workspace select staging
    terraform apply -var-file="terraform.staging.tfvars" -auto-approve
elif [ "$ENVIRONMENT" = "production" ]; then
    terraform workspace select default
    terraform apply -var-file="terraform.tfvars" -auto-approve
else
    echo "Usage: $0 [staging|production]"
    exit 1
fi
```

## Cleanup/Destroy

### Destroy Staging Environment
```bash
terraform workspace select staging
terraform destroy -var-file="terraform.staging.tfvars"
```

### Destroy Production Environment
```bash
terraform workspace select default
terraform destroy -var-file="terraform.tfvars"
```

## Troubleshooting

### Common Issues

1. **RDS Connection Issues**: Ensure security groups allow connections from Lambda
2. **Docker Build Failures**: Check that Docker is running and AWS credentials are configured
3. **Cloudflare DNS Issues**: Verify the API key and domain settings

### Useful Commands
```bash
# Check workspace state
terraform workspace show

# List all resources in current workspace
terraform state list

# Get specific resource details
terraform state show aws_lambda_function.backend_lambda

# Force refresh state
terraform refresh -var-file="terraform.staging.tfvars"
```

## Security Considerations

1. **Database Password**: The staging environment uses the same RDS password as production
2. **Separate Secrets**: Consider using different API keys for staging vs production
3. **Network Security**: Both environments share the same VPC and security groups

## Next Steps

1. **Environment-Specific Secrets**: Set up AWS Secrets Manager for environment-specific configurations
2. **Monitoring**: Set up separate CloudWatch dashboards for staging
3. **Backup Strategy**: Implement separate backup strategies for staging data
4. **Testing Pipeline**: Automate testing against staging environment before production deployment

---

## ✅ DEPLOYMENT STATUS (Updated)

### Issues Fixed

1. **VPC Endpoint Conflicts**: Modified VPC endpoints to only be created for dev environment, staging references existing ones
2. **RDS Sharing**: Configured staging to use existing dev RDS instance with separate database
3. **Docker Build Optimization**: Enhanced error handling for Docker builds to handle keychain conflicts
4. **Dependencies**: Removed dynamic dependencies that aren't supported in Terraform

### Current Status

✅ **Plan Validated**: `terraform plan -var-file="terraform.staging.tfvars"` runs successfully  
✅ **VPC Endpoint Issue Resolved**: Staging uses existing VPC endpoints from dev  
✅ **Docker Build Fixed**: Enhanced error handling for ECR login issues  
✅ **Ready for Deployment**: 8 resources to add, 1 to replace  

### Next Steps

Once you're ready to deploy:

```bash
# Apply the staging environment (when you're ready)
terraform apply -var-file="terraform.staging.tfvars"
```

**What the deployment will do**:
- ✅ Create 8 new staging resources
- ✅ Build and push staging Docker images 
- ✅ Share existing VPC endpoints and RDS with production
- ✅ Set up staging website at `staging.avantifellows.org`
- ✅ Create staging database in existing RDS instance 