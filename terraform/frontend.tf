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

# --- CloudFront Origin Access Control (OAC) for S3 ---
# Using OAC instead of OAI as it's the newer recommended approach
resource "aws_cloudfront_origin_access_control" "frontend_oac" {
  name                              = "${var.project_name}-frontend-${var.environment}-oac"
  description                       = "Origin Access Control for ${var.project_name} frontend S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# Update bucket policy to only allow CloudFront OAC access
data "aws_iam_policy_document" "frontend_bucket_policy" {
  statement {
    sid       = "AllowCloudFrontServicePrincipal"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend_bucket.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.frontend_distribution.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "frontend_bucket_policy" {
  bucket = aws_s3_bucket.frontend_bucket.id
  policy = data.aws_iam_policy_document.frontend_bucket_policy.json

  depends_on = [aws_cloudfront_distribution.frontend_distribution]
}

# Block public access since CloudFront will serve the content
resource "aws_s3_bucket_public_access_block" "frontend_bucket_pab" {
  bucket = aws_s3_bucket.frontend_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- CloudFront Response Headers Policy for CORS ---
resource "aws_cloudfront_response_headers_policy" "frontend_cors_policy" {
  name    = "${var.project_name}-frontend-${var.environment}-cors-policy"
  comment = "CORS policy for ${var.project_name} frontend"

  cors_config {
    access_control_allow_credentials = false

    access_control_allow_headers {
      items = ["*"]
    }

    access_control_allow_methods {
      items = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    }

    access_control_allow_origins {
      items = ["*"]
    }

    access_control_expose_headers {
      items = ["*"]
    }

    access_control_max_age_sec = 86400

    origin_override = false
  }

  security_headers_config {
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      override                   = false
    }
    content_type_options {
      override = false
    }
    frame_options {
      frame_option = "DENY"
      override     = false
    }
    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = false
    }
  }
}

# --- CloudFront Distribution ---
resource "aws_cloudfront_distribution" "frontend_distribution" {
  origin {
    domain_name              = aws_s3_bucket.frontend_bucket.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.frontend_bucket.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.frontend_oac.id
  }

  enabled             = true
  is_ipv6_enabled     = true
  comment             = "CloudFront distribution for ${var.project_name}-frontend-${var.environment}"
  default_root_object = "index.html"

  # Custom error pages for SPA routing
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  default_cache_behavior {
    allowed_methods                = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods                 = ["GET", "HEAD", "OPTIONS"]
    target_origin_id               = "S3-${aws_s3_bucket.frontend_bucket.id}"
    response_headers_policy_id     = aws_cloudfront_response_headers_policy.frontend_cors_policy.id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400    # 1 day
    max_ttl                = 31536000 # 1 year

    # Enable compression
    compress = true
  }

  # Cache behavior for static assets (CSS, JS, images)
  ordered_cache_behavior {
    path_pattern             = "/static/*"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    target_origin_id         = "S3-${aws_s3_bucket.frontend_bucket.id}"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_cors_policy.id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 31536000 # 1 year for static assets
    max_ttl                = 31536000 # 1 year
    compress               = true
  }

  # Cache behavior for assets directory
  ordered_cache_behavior {
    path_pattern             = "/assets/*"
    allowed_methods          = ["GET", "HEAD", "OPTIONS"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    target_origin_id         = "S3-${aws_s3_bucket.frontend_bucket.id}"
    response_headers_policy_id = aws_cloudfront_response_headers_policy.frontend_cors_policy.id

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 31536000 # 1 year for assets
    max_ttl                = 31536000 # 1 year
    compress               = true
  }

  # Price class - affects cost and performance globally
  price_class = "PriceClass_100" # Use PriceClass_All for best performance globally

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL certificate (using default CloudFront cert)
  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = {
    Name        = "${var.project_name}-frontend-${var.environment}-cf"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Component   = "Frontend"
  }
}

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