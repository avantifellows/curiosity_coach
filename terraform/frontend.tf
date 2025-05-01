# terraform/frontend.tf

# --- Frontend S3 Bucket ---

resource "aws_s3_bucket" "frontend_bucket" {
  bucket = "${var.project_name}-frontend-${var.environment}" # Example: curiosity-coach-frontend-dev
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-frontend-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Component   = "Frontend"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend_website" {
  bucket = aws_s3_bucket.frontend_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html" # Or specific error page like error.html if you have one
  }
}

# Allow Public access for S3 static website hosting
resource "aws_s3_bucket_public_access_block" "frontend_bucket_pab" {
  bucket = aws_s3_bucket.frontend_bucket.id

  # block_public_acls       = true # Keep false or remove to allow public ACLs if needed by static hosting
  # block_public_policy     = true # Keep false or remove to allow public bucket policy
  block_public_acls       = false # Allow setting public ACLs if needed for static hosting
  block_public_policy     = false # Allow public bucket policies for static hosting
  ignore_public_acls      = false
  restrict_public_buckets = false # Allow public access via the website endpoint
}

# --- Public Access Policy for S3 Website Hosting ---

data "aws_iam_policy_document" "frontend_bucket_website_policy" {
  statement {
    sid       = "PublicReadGetObject"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend_bucket.arn}/*"] # Policy applies to objects in the bucket

    principals {
      type        = "*" # Allows anyone
      identifiers = ["*"]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_bucket_website_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id
  policy = data.aws_iam_policy_document.frontend_bucket_website_policy.json

  # Ensure the policy depends on the public access block being configured
  depends_on = [aws_s3_bucket_public_access_block.frontend_bucket_pab]
}

/*
# CloudFront Origin Access Identity
resource "aws_cloudfront_origin_access_identity" "frontend_oai" {
  comment = "OAI for ${aws_s3_bucket.frontend_bucket.id}"
}

# Bucket policy to allow CloudFront OAI read access
data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend_bucket.arn}/*"]

    principals {
      type        = "AWS"
      identifiers = [aws_cloudfront_origin_access_identity.frontend_oai.iam_arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_bucket_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy.json
}
*/

/*
# --- CloudFront Distribution ---

resource "aws_cloudfront_distribution" "frontend_distribution" {
  origin {
    domain_name = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name # Use regional domain name
    origin_id   = "S3-${aws_s3_bucket.frontend_bucket.id}"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.frontend_oai.cloudfront_access_identity_path
    }
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.project_name}-frontend-${var.environment}"
  default_root_object = "index.html"

  # Logging configuration (optional but recommended)
  # logging_config {
  #   include_cookies = false
  #   bucket          = "your-cloudfront-logs-bucket.s3.amazonaws.com" # Create a separate bucket for logs
  #   prefix          = "frontend-cloudfront/"
  # }

  # Aliases (custom domain names - optional)
  # aliases = ["www.yourdomain.com", "yourdomain.com"]

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.frontend_bucket.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600 # 1 hour
    max_ttl                = 86400 # 24 hours
  }

  # Price class - affects cost and performance globally
  # Options: PriceClass_All, PriceClass_200, PriceClass_100
  price_class = "PriceClass_100" # Use PriceClass_All for best performance globally

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL certificate (using default CloudFront cert)
  viewer_certificate {
    cloudfront_default_certificate = true
    # If using custom domain + ACM certificate:
    # acm_certificate_arn = var.acm_certificate_arn # Define this variable if needed
    # ssl_support_method  = "sni-only"
    # minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = {
    Name        = "${var.project_name}-frontend-${var.environment}-cf"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Component   = "Frontend"
  }
}
*/

# --- Outputs ---

output "frontend_s3_bucket_name" {
  description = "The name of the S3 bucket storing the frontend assets."
  value       = aws_s3_bucket.frontend_bucket.id
}

output "frontend_s3_bucket_arn" {
  description = "The ARN of the S3 bucket storing the frontend assets."
  value       = aws_s3_bucket.frontend_bucket.arn
}

# Output for the S3 static website endpoint
output "frontend_s3_website_endpoint" {
  description = "The public website endpoint URL for the S3 bucket."
  value       = aws_s3_bucket_website_configuration.frontend_website.website_endpoint
}

/*
output "frontend_cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution for the frontend."
  value       = aws_cloudfront_distribution.frontend_distribution.id
}

output "frontend_cloudfront_domain_name" {
  description = "The domain name of the CloudFront distribution (URL for the frontend)."
  value       = aws_cloudfront_distribution.frontend_distribution.domain_name
}

output "frontend_url" {
  description = "The HTTPS URL for the frontend."
  value       = "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}"
}
*/ 