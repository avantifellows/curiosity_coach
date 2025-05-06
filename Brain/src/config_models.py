from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import json
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from src.utils.logger import logger # Assuming logger is appropriately accessible

class FlowConfig(BaseModel):
    """Configuration for the query processing flow."""
    run_enhancement_step: Optional[bool] = Field(
        default=True,
        description="Set to false to skip the learning enhancement step and return the initial response directly."
    )

    @classmethod
    def init(cls) -> Optional[Dict[str, Any]]:
        """Creates a default configuration and uploads it to S3."""
        bucket_name = os.getenv("FLOW_CONFIG_S3_BUCKET_NAME")
        object_key = os.getenv("FLOW_CONFIG_S3_KEY", "flow_config.json")

        if not bucket_name:
            logger.error("FLOW_CONFIG_S3_BUCKET_NAME not set. Cannot initialize default config in S3.")
            return None

        # Create default configuration based on the model's defaults
        default_config = cls().model_dump(exclude_none=True)
        logger.info(f"Generated default FlowConfig: {default_config}")

        s3_client = boto3.client('s3')
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=json.dumps(default_config, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Successfully uploaded default config to S3: s3://{bucket_name}/{object_key}")
            return default_config
        except ClientError as e:
            logger.error(f"S3 ClientError when uploading default config to s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        except (NoCredentialsError, PartialCredentialsError):
            logger.error("AWS credentials not found or incomplete for S3 access during init.")
        except Exception as e:
            logger.error(f"Failed to upload default config to s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        return None

    @classmethod
    def get_config_from_s3(cls) -> Optional[Dict[str, Any]]:
        bucket_name = os.getenv("FLOW_CONFIG_S3_BUCKET_NAME")
        object_key = os.getenv("FLOW_CONFIG_S3_KEY", "flow_config.json") # Default to flow_config.json

        if not bucket_name:
            logger.info("FLOW_CONFIG_S3_BUCKET_NAME not set. Skipping S3 config load.")
            return None

        s3_client = boto3.client('s3')
        try:
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            config_data = json.loads(response['Body'].read().decode('utf-8'))
            # Validate with Pydantic model
            parsed_config = cls(**config_data)
            logger.info(f"Successfully loaded and validated config from S3: s3://{bucket_name}/{object_key}")
            return parsed_config.model_dump(exclude_none=True)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Config file s3://{bucket_name}/{object_key} not found. Attempting to initialize.")
                # Call init to create and upload the default config
                return cls.init()
            elif e.response['Error']['Code'] == 'NoSuchBucket':
                logger.warning(f"S3 bucket '{bucket_name}' not found.")
            else:
                logger.error(f"S3 ClientError when fetching config from s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        except (NoCredentialsError, PartialCredentialsError):
            logger.error("AWS credentials not found or incomplete for S3 access.")
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from config file s3://{bucket_name}/{object_key}.", exc_info=True)
        except Exception as e: # Catch any other exceptions, including Pydantic validation errors
            logger.error(f"Failed to load or parse config from s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        return None 