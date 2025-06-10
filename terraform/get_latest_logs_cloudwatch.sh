#!/bin/bash

# A simple script to fetch the latest n logs from a CloudWatch log group.
#
# Usage: ./get_latest_logs.sh "<log-group-arn>" <number-of-events>
#
# Example:
# ./get_latest_logs.sh "arn:aws:logs:us-east-1:123456789012:log-group:/my/log/group:* 10"
#
# The ARN should be quoted to prevent the shell from interpreting characters like '*'.
#
# Prerequisites:
# - AWS CLI installed and configured with necessary permissions.
#   (Permissions needed: logs:DescribeLogStreams, logs:GetLogEvents)

set -e
set -o pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 \"<log-group-arn>\" <number-of-events>"
    echo "Example: $0 \"arn:aws:logs:us-east-1:123456789012:log-group:/my/log/group:*\" 10"
    exit 1
fi

LOG_GROUP_ARN=$1
LIMIT=$2

# Basic validation for the limit
if ! [[ "$LIMIT" =~ ^[0-9]+$ ]] || [ "$LIMIT" -le 0 ]; then
    echo "Error: Number of events must be a positive integer."
    exit 1
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

# Find the latest log stream
echo "Finding the latest log stream in '$LOG_GROUP_NAME'..."
LATEST_STREAM_NAME=$(aws logs describe-log-streams \
    --region ap-south-1 \
    --log-group-name "$LOG_GROUP_NAME" \
    --order-by LastEventTime \
    --descending \
    --limit 1 \
    --query "logStreams[0].logStreamName" \
    --output text)

if [ "$LATEST_STREAM_NAME" = "None" ] || [ -z "$LATEST_STREAM_NAME" ]; then
    echo "Error: No log streams found in log group '$LOG_GROUP_NAME'."
    exit 1
fi

echo "Found latest log stream: $LATEST_STREAM_NAME"
echo "Fetching the last $LIMIT log events..."
echo ""

# Fetch the latest N log events from the stream
# We can't use the JMESPath from_millis function as it's not available in all aws-cli versions.
# Instead, we get the raw data and format it with shell commands.
LOG_EVENTS=$(aws logs get-log-events \
    --region ap-south-1 \
    --log-group-name "$LOG_GROUP_NAME" \
    --log-stream-name "$LATEST_STREAM_NAME" \
    --limit "$LIMIT" \
    --query "events[].[timestamp, message]" \
    --output text)

if [ -z "$LOG_EVENTS" ]; then
    echo "No log events found in the stream."
    exit 0
fi

# Print header for our table
printf "%-24s %s\n" "Time" "Message"
printf "%-24s %s\n" "------------------------" "--------------------------------------------------"

# Process and print each log event
# We set IFS to tab to correctly handle log messages with spaces.
echo "$LOG_EVENTS" | while IFS=$'\t' read -r timestamp message; do
    # Convert timestamp from milliseconds to seconds for the 'date' command
    seconds=$((timestamp / 1000))
    # Format the timestamp (supports macOS/BSD date command)
    formatted_time=$(date -r "$seconds" '+%Y-%m-%d %H:%M:%S UTC')
    printf "%-24s %s\n" "$formatted_time" "$message"
done


echo ""
echo "Done." 