# https://medium.com/@sebastian.phelps/aws-cloudwatch-alarms-on-microsoft-teams-9b5239e23b64
import json
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

HOOK_URL = os.environ['TEAMS_WEBHOOK_URL']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Emoji constants for different notification types
EMOJI_SECRET = "🔐"  # Secret/security related
EMOJI_CLOUDTRAIL = "☁️"  # Cloud services
EMOJI_DEPLOYMENT = "🚀"  # Deployments/releases
EMOJI_WARNING = "⚠️"  # Warnings/drift
EMOJI_ERROR = "❌"  # Errors
EMOJI_SUCCESS = "✅"  # Success
EMOJI_INFO = "ℹ️"  # Information
EMOJI_TIME = "🕒"  # Timestamp
EMOJI_USER = "👤"  # User/deployer
EMOJI_VERSION = "🏷️"  # Version tags
EMOJI_TARGET = "🎯"  # Target/destination
EMOJI_NAMESPACE = "📁"  # Namespace/folder


def get_action_color(action: str) -> str:
    """Returns the appropriate color for the action text based on the action value"""
    action_lower = action.lower()
    if action_lower in ["deleted", "d", "delete", "removed"]:
        return "attention"  # Red color for destructive actions
    elif action_lower in ["created", "create", "added"]:
        return "good"  # Green color for creation actions
    elif action_lower in ["updated", "update", "modified"]:
        return "default"  # Blue/default color for update actions
    elif action_lower in ["deployed", "deploy"]:
        return "good"  # Green color for successful deployments
    elif action_lower in ["restored", "restore"]:
        return "good"  # Green color for restoration actions
    else:
        return "default"  # Default blue color for unknown actions


class FactSet:
    def __init__(self, title: str, value: str):
        self.title = title
        self.value = value
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "value": self.value
        }


class ColumnSet:
    def __init__(self, type_: str = "Column", width: Optional[str] = None, items: Optional[List['BodyBlock']] = None):
        self.type = type_
        self.width = width
        self.items = items or []
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "items": [item.to_dict() for item in self.items]
        }
        if self.width:
            result["width"] = self.width
        return result


class BodyBlock:
    def __init__(self, type_: str, text: Optional[str] = None, weight: Optional[str] = None, 
                 size: Optional[str] = None, color: Optional[str] = None, facts: Optional[List[FactSet]] = None,
                 columns: Optional[List[ColumnSet]] = None, items: Optional[List['BodyBlock']] = None,
                 style: Optional[str] = None, spacing: Optional[str] = None, separator: Optional[bool] = None,
                 horizontal_alignment: Optional[str] = None, vertical_content_alignment: Optional[str] = None,
                 wrap: Optional[bool] = None):
        self.type = type_
        self.text = text
        self.weight = weight
        self.size = size
        self.color = color
        self.facts = facts or []
        self.columns = columns or []
        self.items = items or []
        self.style = style
        self.spacing = spacing
        self.separator = separator
        self.horizontal_alignment = horizontal_alignment
        self.vertical_content_alignment = vertical_content_alignment
        self.wrap = wrap
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        
        if self.text is not None:
            result["text"] = self.text
        if self.weight is not None:
            result["weight"] = self.weight
        if self.size is not None:
            result["size"] = self.size
        if self.color is not None:
            result["color"] = self.color
        if self.facts:
            result["facts"] = [fact.to_dict() for fact in self.facts]
        if self.columns:
            result["columns"] = [column.to_dict() for column in self.columns]
        if self.items:
            result["items"] = [item.to_dict() for item in self.items]
        if self.style is not None:
            result["style"] = self.style
        if self.spacing is not None:
            result["spacing"] = self.spacing
        if self.separator is not None:
            result["separator"] = self.separator
        if self.horizontal_alignment is not None:
            result["horizontalAlignment"] = self.horizontal_alignment
        if self.vertical_content_alignment is not None:
            result["verticalContentAlignment"] = self.vertical_content_alignment
        if self.wrap is not None:
            result["wrap"] = self.wrap
            
        return result


class Content:
    def __init__(self, schema: str = "http://adaptivecards.io/schemas/adaptive-card.json",
                 type_: str = "AdaptiveCard", version: str = "1.2", body: Optional[List[BodyBlock]] = None):
        self.schema = schema
        self.type = type_
        self.version = version
        self.body = body or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "$schema": self.schema,
            "type": self.type,
            "version": self.version,
            "body": [block.to_dict() for block in self.body]
        }


class Attachment:
    def __init__(self, content_type: str = "application/vnd.microsoft.card.adaptive",
                 content_url: Optional[Any] = None, content: Optional[Content] = None):
        self.content_type = content_type
        self.content_url = content_url
        self.content = content
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contentType": self.content_type,
            "contentUrl": self.content_url,
            "content": self.content.to_dict() if self.content else {}
        }


class TeamsMessage:
    def __init__(self, type_: str = "message", attachments: Optional[List[Attachment]] = None):
        self.type = type_
        self.attachments = attachments or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "attachments": [attachment.to_dict() for attachment in self.attachments]
        }

def create_cloudtrail_message(message_json_detail: Dict[str, Any]) -> TeamsMessage:
    """Create an adaptive card message for CloudTrail events"""
    logger.info("message_json_detail: %s", json.dumps(message_json_detail))

    alarm_name = message_json_detail.get('eventName', 'Unknown Event')
    event_type = message_json_detail.get('eventType', 'Unknown Type')
    event_id = message_json_detail.get('eventID', 'Unknown ID')
    event_time = message_json_detail.get('eventTime', 'Unknown Time')
    reason = message_json_detail.get('errorMessage', 'No error message provided')

    # Create the adaptive card content
    content = Content(
        body=[
            BodyBlock(
                type_="Container",
                style="good",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_CLOUDTRAIL} {EMOJI_SUCCESS} CloudTrail Event",
                        weight="Bolder",
                        size="Large",
                        color="Good",
                        wrap=True
                    )
                ],
                spacing="Medium"
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="ColumnSet",
                        columns=[
                            ColumnSet(
                                width="auto",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=f"{EMOJI_TARGET} **Action:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="🌍 **Type:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="🔗 **Event ID:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=f"{EMOJI_TIME} **Timestamp:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            ),
                            ColumnSet(
                                width="stretch",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=alarm_name,
                                        color="good",
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=event_type,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=event_id,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=event_time,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            BodyBlock(
                type_="Container",
                style="attention",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_ERROR} Error Details",
                        weight="Bolder",
                        size="Medium",
                        color="attention",
                        wrap=True
                    ),
                    BodyBlock(
                        type_="Container",
                        style="default",
                        spacing="Small",
                        items=[
                            BodyBlock(
                                type_="TextBlock",
                                text=reason,
                                color="attention",
                                wrap=True,
                                weight="Default"
                            )
                        ]
                    )
                ]
            )
        ]
    )

    attachment = Attachment(content=content)
    return TeamsMessage(attachments=[attachment])



def create_cloudwatch_alarm_message(message_json: Dict[str, Any]) -> TeamsMessage:
    """Create an adaptive card message for CloudWatch alarms"""
    alarm_name = message_json.get('AlarmName', 'Unknown Alarm')
    old_state = message_json.get('OldStateValue', 'Unknown')
    new_state = message_json.get('NewStateValue', 'Unknown')
    reason = message_json.get('NewStateReason', 'No reason provided')
    timestamp = message_json.get('StateChangeTime', datetime.now().isoformat())

    # Determine message style and colors based on alarm state
    if new_state.lower() == 'alarm':
        style = "attention"
        title_color = "Attention"
        title_text = f"{EMOJI_ERROR} {EMOJI_WARNING} CloudWatch Alarm - {alarm_name}"
        state_color = "attention"
    else:
        style = "good"
        title_color = "Good"
        title_text = f"{EMOJI_SUCCESS} {EMOJI_INFO} CloudWatch Alarm Resolved - {alarm_name}"
        state_color = "good"

    content = Content(
        body=[
            BodyBlock(
                type_="Container",
                style=style,
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=title_text,
                        weight="Bolder",
                        size="Large",
                        color=title_color,
                        wrap=True
                    )
                ],
                spacing="Medium"
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="ColumnSet",
                        columns=[
                            ColumnSet(
                                width="auto",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=f"{EMOJI_TARGET} **Alarm:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="📊 **Old State:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="📈 **New State:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=f"{EMOJI_TIME} **Timestamp:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            ),
                            ColumnSet(
                                width="stretch",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=alarm_name,
                                        color=state_color,
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=old_state,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=new_state,
                                        color=state_color,
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=timestamp,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_INFO} **Reason:**",
                        weight="Bolder",
                        size="Medium",
                        color="default",
                        wrap=True
                    ),
                    BodyBlock(
                        type_="TextBlock",
                        text=reason,
                        color="default",
                        wrap=True,
                        spacing="Small"
                    )
                ]
            )
        ]
    )

    attachment = Attachment(content=content)
    return TeamsMessage(attachments=[attachment])


def create_generic_message(sns_record: Dict[str, Any]) -> TeamsMessage:
    """Create a generic adaptive card message for other SNS events"""
    subject = sns_record.get('Subject', 'Unknown Subject')
    message_body = sns_record.get('Message', 'No message body')
    timestamp = sns_record.get('Timestamp', datetime.now().isoformat())
    topic_arn = sns_record.get('TopicArn', 'Unknown Topic')
    message_id = sns_record.get('MessageId', 'Unknown Message ID')

    content = Content(
        body=[
            BodyBlock(
                type_="Container",
                style="attention",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_WARNING} {EMOJI_INFO} AWS Notification - {subject}",
                        weight="Bolder",
                        size="Large",
                        color="Attention",
                        wrap=True
                    )
                ],
                spacing="Medium"
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="ColumnSet",
                        columns=[
                            ColumnSet(
                                width="auto",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="📋 **Subject:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="🔗 **Topic ARN:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text="🆔 **Message ID:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=f"{EMOJI_TIME} **Timestamp:**",
                                        weight="Bolder",
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            ),
                            ColumnSet(
                                width="stretch",
                                items=[
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=subject,
                                        color="attention",
                                        wrap=True
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=topic_arn,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=message_id,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    ),
                                    BodyBlock(
                                        type_="TextBlock",
                                        text=timestamp,
                                        color="default",
                                        wrap=True,
                                        spacing="Small"
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_INFO} **Message:**",
                        weight="Bolder",
                        size="Medium",
                        color="default",
                        wrap=True
                    ),
                    BodyBlock(
                        type_="TextBlock",
                        text=message_body,
                        color="default",
                        wrap=True,
                        spacing="Small"
                    )
                ]
            )
        ]
    )

    attachment = Attachment(content=content)
    return TeamsMessage(attachments=[attachment])


def send_teams_message(teams_message: TeamsMessage) -> None:
    """Send the adaptive card message to Teams"""
    message_dict = teams_message.to_dict()
    
    # Explicitly set Content-Type to 'application/json'
    req = Request(HOOK_URL, json.dumps(message_dict).encode('utf-8'), 
                  headers={'Content-Type': 'application/json'})
    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted successfully")
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)


def lambda_handler(event, context):
    logger.info("Event: %s", json.dumps(event))
    
    try:
        message = event['Records'][0]['Sns']['Message']
        message_json = json.loads(message)
        sns_record = event['Records'][0]['Sns']

        teams_message = None

        if 'AlarmName' in message_json:
            if is_cloudwatch_alarm(message):
                logger.info("Processing CloudWatch alarm message")
                teams_message = create_cloudwatch_alarm_message(message_json)
            else:
                logger.info("Processing generic SNS message")
                teams_message = create_generic_message(sns_record)
        elif 'detail-type' in message_json and message_json['detail-type'] == 'AWS Service Event via CloudTrail':
            logger.info("Processing CloudTrail message")
            teams_message = create_cloudtrail_message(message_json['detail'])
        else:
            logger.info("Processing generic SNS message - no specific handler found")
            teams_message = create_generic_message(sns_record)

        if teams_message:
            send_teams_message(teams_message)
        else:
            logger.error("Failed to create Teams message")

    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        # Create error message
        error_message = create_error_message(str(e))
        send_teams_message(error_message)


def create_error_message(error_text: str) -> TeamsMessage:
    """Create an error message for Teams"""
    content = Content(
        body=[
            BodyBlock(
                type_="Container",
                style="attention",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_ERROR} {EMOJI_WARNING} Lambda Function Error",
                        weight="Bolder",
                        size="Large",
                        color="Attention",
                        wrap=True
                    )
                ],
                spacing="Medium"
            ),
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Medium",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_ERROR} **Error Details:**",
                        weight="Bolder",
                        size="Medium",
                        color="attention",
                        wrap=True
                    ),
                    BodyBlock(
                        type_="TextBlock",
                        text=error_text,
                        color="attention",
                        wrap=True,
                        spacing="Small"
                    ),
                    BodyBlock(
                        type_="TextBlock",
                        text=f"{EMOJI_TIME} **Timestamp:**",
                        weight="Bolder",
                        color="default",
                        wrap=True,
                        spacing="Small"
                    ),
                    BodyBlock(
                        type_="TextBlock",
                        text=datetime.now().isoformat(),
                        color="default",
                        wrap=True,
                        spacing="Small"
                    )
                ]
            )
        ]
    )

    attachment = Attachment(content=content)
    return TeamsMessage(attachments=[attachment])


def is_cloudwatch_alarm(message):
    try:
        message_json = json.loads(message)
        if message_json['AlarmName']:
            return True
        else:
            return False
    except ValueError as e:
        return False
