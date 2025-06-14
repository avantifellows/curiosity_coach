#!/bin/bash

# A simple script to fetch the latest n logs from a CloudWatch log group.
#
# Usage: ./get_latest_logs_cloudwatch.sh "<log-group-short-name|log-group-arn>" <number-of-events>
#
# Example using short name:
# ./get_latest_logs_cloudwatch.sh "backend-staging" 500
#
# Example using ARN:
# ./get_latest_logs_cloudwatch.sh "arn:aws:logs:us-east-1:123456789012:log-group:/my/log/group:*\" 10
#
# The ARN should be quoted to prevent the shell from interpreting characters like '*'.
#
# Prerequisites:
# - AWS CLI installed and configured with necessary permissions.
#   (Permissions needed: logs:DescribeLogStreams, logs:GetLogEvents)

set -e
set -o pipefail

# --- Configuration for short names ---
get_arn_from_short_name() {
    case "$1" in
        "backend-staging")
            echo "arn:aws:logs:ap-south-1:111766607077:log-group:/aws/lambda/curiosity-coach-backend-staging-lambda:*"
            ;;
        "backend-prod")
            echo "arn:aws:logs:ap-south-1:111766607077:log-group:/aws/lambda/curiosity-coach-backend-dev-lambda:*"
            ;;
        "brain-staging")
            echo "arn:aws:logs:ap-south-1:111766607077:log-group:/aws/lambda/curiosity-coach-brain-staging-lambda:*"
            ;;
        "brain-prod")
            echo "arn:aws:logs:ap-south-1:111766607077:log-group:/aws/lambda/curiosity-coach-brain-lambda:*"
            ;;
        *)
            # Return nothing if no match
            ;;
    esac
}
# -------------------------------------

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 \"<log-group-short-name|log-group-arn>\" <number-of-events>"
    echo "Example (short name): $0 \"backend-staging\" 500"
    echo "Example (ARN): $0 \"arn:aws:logs:us-east-1:123456789012:log-group:/my/log/group:*\" 10"
    exit 1
fi

INPUT_ID=$1
LIMIT=$2
NUM_STREAMS_TO_CHECK=20 # Number of recent streams to check for logs

# Basic validation for the limit
if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [ "$LIMIT" -le 0 ]; then
    echo "Error: Number of events must be a positive integer."
    exit 1
fi

LOG_GROUP_ARN=$(get_arn_from_short_name "$INPUT_ID")

if [ -n "$LOG_GROUP_ARN" ]; then
    echo "Found short name '$INPUT_ID'. Using ARN: $LOG_GROUP_ARN"
else
    # If not a short name, assume it's an ARN
    LOG_GROUP_ARN=$INPUT_ID
    echo "Using provided ARN: $LOG_GROUP_ARN"
fi

# Extract log group name from ARN.
# ARN format: arn:aws:logs:REGION:ACCOUNT_ID:log-group:LOG_GROUP_NAME:*
# We extract the part after 'log-group:' and remove the optional trailing ':*'
TEMP_NAME=${LOG_GROUP_ARN#*:log-group:}
LOG_GROUP_NAME=${TEMP_NAME%:\*}


if [ "$LOG_GROUP_NAME" = "$LOG_GROUP_ARN" ] || [ -z "$LOG_GROUP_NAME" ]; then
    echo "Error: Could not parse log group name from ARN: $LOG_GROUP_ARN" >&2
    echo "Please ensure the ARN is in the correct format, e.g., arn:aws:logs:us-east-1:123456789012:log-group:my-log-group:*" >&2
    exit 1
fi

echo "Log Group Name: $LOG_GROUP_NAME"
echo ""

# Check if aws-cli is available
if ! command -v aws &> /dev/null
then
    echo "AWS CLI could not be found. Please install and configure it."
    exit 1
fi

# Find the latest log streams
echo "Finding the latest $NUM_STREAMS_TO_CHECK log streams in '$LOG_GROUP_NAME'..."
LOG_STREAM_NAMES=$(aws logs describe-log-streams \
    --region ap-south-1 \
    --log-group-name "$LOG_GROUP_NAME" \
    --order-by LastEventTime \
    --descending \
    --limit $NUM_STREAMS_TO_CHECK \
    --query "logStreams[].logStreamName" \
    --output text)

if [ -z "$LOG_STREAM_NAMES" ]; then
    echo "Error: No log streams found in log group '$LOG_GROUP_NAME'."
    exit 1
fi

echo "Found latest log streams. Fetching the last $LIMIT log events..."
echo ""

# Fetch the latest N log events from the streams
all_log_events=""
for stream_name in $LOG_STREAM_NAMES; do
    events=$(aws logs get-log-events \
        --region ap-south-1 \
        --log-group-name "$LOG_GROUP_NAME" \
        --log-stream-name "$stream_name" \
        --limit "$LIMIT" \
        --query "events[].[timestamp, message]" \
        --output text 2>/dev/null) || true
    
    if [ -n "$events" ]; then
        all_log_events="${all_log_events}${events}"$'\n'
    fi
done

if [ -z "$all_log_events" ]; then
    echo "No log events found in the checked streams."
    exit 0
fi

# Sort all collected events by timestamp (newest first) and take the top N
# We use sort -u to remove duplicate events that might be fetched from overlapping stream reads
# Temporarily disable pipefail as `head` will close the pipe and cause `sort` to receive a
# SIGPIPE, which would otherwise cause the script to exit.
set +o pipefail
sorted_events=$(echo -n "$all_log_events" | sort -u -k1,1 -n -r | head -n "$LIMIT")
set -o pipefail

# Print header for our table
printf "%-24s %s\n" "Time" "Message"
printf "%-24s %s\n" "------------------------" "--------------------------------------------------"

# Process and print each log event
# We set IFS to tab to correctly handle log messages with spaces.
echo "$sorted_events" | while IFS=$'\t' read -r timestamp message; do
    if [ -z "$timestamp" ]; then continue; fi
    # Convert timestamp from milliseconds to seconds for the 'date' command
    seconds=$((timestamp / 1000))
    # Format the timestamp (supports macOS/BSD date command)
    formatted_time=$(date -r "$seconds" '+%Y-%m-%d %H:%M:%S UTC')
    printf "%-24s %s\n" "$formatted_time" "$message"
done


echo ""
echo "Done." 