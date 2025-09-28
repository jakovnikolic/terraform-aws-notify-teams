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


class Fact:
    def __init__(self, title: str, value: str):
        self.title = title
        self.value = value
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "value": self.value
        }


class FactSetBlock:
    def __init__(self, facts: List[Fact], spacing: Optional[str] = None, separator: Optional[bool] = None):
        self.facts = facts
        self.spacing = spacing
        self.separator = separator
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "FactSet",
            "facts": [fact.to_dict() for fact in self.facts]
        }
        if self.spacing:
            result["spacing"] = self.spacing
        if self.separator is not None:
            result["separator"] = self.separator
        return result


class Action:
    def __init__(self, type_: str, title: str, url: Optional[str] = None, style: Optional[str] = None):
        self.type = type_
        self.title = title
        self.url = url
        self.style = style
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "title": self.title
        }
        if self.url:
            result["url"] = self.url
        if self.style:
            result["style"] = self.style
        return result


class TableColumn:
    def __init__(self, width: Optional[str] = None):
        self.width = width
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"type": "TableColumnDefinition"}
        if self.width:
            result["width"] = self.width
        return result


class TableCell:
    def __init__(self, items: List['BodyBlock']):
        self.items = items
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "TableCell",
            "items": [item.to_dict() for item in self.items]
        }


class TableRow:
    def __init__(self, cells: List[TableCell]):
        self.cells = cells
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "TableRow",
            "cells": [cell.to_dict() for cell in self.cells]
        }


class Table:
    def __init__(self, columns: List[TableColumn], rows: List[TableRow], first_row_as_header: bool = True,
                 show_grid_lines: bool = False, spacing: Optional[str] = None):
        self.columns = columns
        self.rows = rows
        self.first_row_as_header = first_row_as_header
        self.show_grid_lines = show_grid_lines
        self.spacing = spacing
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "Table",
            "columns": [column.to_dict() for column in self.columns],
            "rows": [row.to_dict() for row in self.rows],
            "firstRowAsHeader": self.first_row_as_header,
            "showGridLines": self.show_grid_lines
        }
        if self.spacing:
            result["spacing"] = self.spacing
        return result


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
    def __init__(self, type_: str = None, text: Optional[str] = None, weight: Optional[str] = None, 
                 size: Optional[str] = None, color: Optional[str] = None, facts: Optional[List[FactSet]] = None,
                 columns: Optional[List[ColumnSet]] = None, items: Optional[List['BodyBlock']] = None,
                 style: Optional[str] = None, spacing: Optional[str] = None, separator: Optional[bool] = None,
                 horizontal_alignment: Optional[str] = None, vertical_content_alignment: Optional[str] = None,
                 wrap: Optional[bool] = None, fact_set_block: Optional[FactSetBlock] = None,
                 table: Optional[Table] = None):
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
        self.fact_set_block = fact_set_block
        self.table = table
    
    def to_dict(self) -> Dict[str, Any]:
        # Handle special cases for FactSet and Table
        if self.fact_set_block:
            return self.fact_set_block.to_dict()
        if self.table:
            return self.table.to_dict()
            
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
                 type_: str = "AdaptiveCard", version: str = "1.2", body: Optional[List[BodyBlock]] = None,
                 actions: Optional[List[Action]] = None):
        self.schema = schema
        self.type = type_
        self.version = version
        self.body = body or []
        self.actions = actions or []
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "$schema": self.schema,
            "type": self.type,
            "version": self.version,
            "body": [block.to_dict() for block in self.body]
        }
        if self.actions:
            result["actions"] = [action.to_dict() for action in self.actions]
        return result


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

def create_cost_anomaly_message(message_json: Dict[str, Any]) -> TeamsMessage:
    """Create an adaptive card message for AWS Cost Anomaly alerts"""
    logger.info("Processing AWS Cost Anomaly message")
    
    # Extract key information
    account_name = message_json.get('accountName', 'Unknown Account')
    monitor_name = message_json.get('monitorName', 'Unknown Monitor')
    anomaly_start = message_json.get('anomalyStartDate', '')
    anomaly_end = message_json.get('anomalyEndDate', '')
    
    # Impact information
    impact = message_json.get('impact', {})
    total_actual = impact.get('totalActualSpend', 0)
    total_expected = impact.get('totalExpectedSpend', 0)
    total_impact = impact.get('totalImpact', 0)
    impact_percentage = impact.get('totalImpactPercentage', 0)
    
    # Anomaly score
    anomaly_score = message_json.get('anomalyScore', {})
    current_score = anomaly_score.get('currentScore', 0)
    max_score = anomaly_score.get('maxScore', 0)
    
    # Root causes (limit to top 5)
    root_causes = message_json.get('rootCauses', [])[:5]
    
    # Anomaly details link
    details_link = message_json.get('anomalyDetailsLink', '')
    
    # Format currency values
    def format_currency(amount):
        return f"${amount:.2f}"
    
    # Create the adaptive card content
    body_blocks = [
        # Header
        BodyBlock(
            type_="Container",
            style="attention",
            items=[
                BodyBlock(
                    type_="TextBlock",
                    text=f"💰 ⚠️ AWS Cost Anomaly Detected",
                    weight="Bolder",
                    size="Large",
                    color="Attention",
                    wrap=True
                )
            ],
            spacing="Medium"
        ),
        
        # Account and Monitor Info
        BodyBlock(
            fact_set_block=FactSetBlock([
                Fact("📊 Account", account_name),
                Fact("🔍 Monitor", monitor_name),
                Fact("📅 Period", f"{anomaly_start[:10]} to {anomaly_end[:10]}"),
                Fact("🎯 Anomaly Score", f"{current_score:.2f} (max: {max_score:.2f})")
            ], spacing="Medium")
        ),
        
        # Cost Impact Summary
        BodyBlock(
            type_="Container",
            style="emphasis",
            spacing="Large",
            items=[
                BodyBlock(
                    type_="TextBlock",
                    text="💸 **Cost Impact Analysis**",
                    weight="Bolder",
                    size="Medium",
                    color="default",
                    wrap=True
                ),
                BodyBlock(
                    type_="ColumnSet",
                    spacing="Medium",
                    columns=[
                        ColumnSet(
                            width="50%",
                            items=[
                                BodyBlock(
                                    type_="TextBlock",
                                    text="**Expected Spend:**",
                                    weight="Bolder",
                                    color="good",
                                    wrap=True
                                ),
                                BodyBlock(
                                    type_="TextBlock",
                                    text=format_currency(total_expected),
                                    color="good",
                                    size="Large",
                                    weight="Bolder",
                                    wrap=True
                                )
                            ]
                        ),
                        ColumnSet(
                            width="50%",
                            items=[
                                BodyBlock(
                                    type_="TextBlock",
                                    text="**Actual Spend:**",
                                    weight="Bolder",
                                    color="attention",
                                    wrap=True
                                ),
                                BodyBlock(
                                    type_="TextBlock",
                                    text=format_currency(total_actual),
                                    color="attention",
                                    size="Large",
                                    weight="Bolder",
                                    wrap=True
                                )
                            ]
                        )
                    ]
                ),
                BodyBlock(
                    type_="Container",
                    style="attention",
                    spacing="Small",
                    items=[
                        BodyBlock(
                            type_="TextBlock",
                            text=f"**Overspend: {format_currency(total_impact)} ({impact_percentage:.1f}% increase)**",
                            weight="Bolder",
                            size="Medium",
                            color="attention",
                            wrap=True,
                            horizontal_alignment="Center"
                        )
                    ]
                )
            ]
        )
    ]
    
    # Add root causes table if available
    if root_causes:
        # Create table columns
        table_columns = [
            TableColumn(width="3"),  # Service (wider)
            TableColumn(width="2"),  # Account
            TableColumn(width="1")   # Impact %
        ]
        
        # Create header row
        header_row = TableRow([
            TableCell([BodyBlock(type_="TextBlock", text="**Service**", weight="Bolder", wrap=True)]),
            TableCell([BodyBlock(type_="TextBlock", text="**Account**", weight="Bolder", wrap=True)]),
            TableCell([BodyBlock(type_="TextBlock", text="**Impact %**", weight="Bolder", wrap=True)])
        ])
        
        # Create data rows
        data_rows = []
        for cause in root_causes:
            service = cause.get('service', 'Unknown Service')
            account_name = cause.get('linkedAccountName', 'Unknown')
            impact_contrib = cause.get('impactContribution', 0)
            
            # Truncate long service names
            if len(service) > 35:
                service = service[:32] + "..."
                
            data_rows.append(TableRow([
                TableCell([BodyBlock(type_="TextBlock", text=service, wrap=True, size="Small")]),
                TableCell([BodyBlock(type_="TextBlock", text=account_name, wrap=True, size="Small")]),
                TableCell([BodyBlock(type_="TextBlock", text=f"{impact_contrib:.1f}%", wrap=True, size="Small", color="attention")])
            ]))
        
        # Add the table to body blocks
        body_blocks.append(
            BodyBlock(
                type_="Container",
                style="default",
                spacing="Large",
                items=[
                    BodyBlock(
                        type_="TextBlock",
                        text=f"🔍 **Top {len(root_causes)} Contributing Services**",
                        weight="Bolder",
                        size="Medium",
                        color="default",
                        wrap=True
                    ),
                    BodyBlock(
                        table=Table(
                            columns=table_columns,
                            rows=[header_row] + data_rows,
                            first_row_as_header=True,
                            show_grid_lines=True,
                            spacing="Small"
                        )
                    )
                ]
            )
        )
    
    # Create actions
    actions = []
    if details_link:
        actions.append(Action(
            type_="Action.OpenUrl",
            title="🔗 View in AWS Console",
            url=details_link,
            style="positive"
        ))
    
    # Create the content
    content = Content(
        body=body_blocks,
        actions=actions
    )
    
    attachment = Attachment(content=content)
    return TeamsMessage(attachments=[attachment])


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


def is_cost_anomaly_message(message_json: Dict[str, Any]) -> bool:
    """Detect if this is an AWS Cost Anomaly message"""
    return (
        'accountId' in message_json and 
        'anomalyId' in message_json and
        'monitorArn' in message_json and
        'impact' in message_json
    )


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
        elif is_cost_anomaly_message(message_json):
            logger.info("Processing AWS Cost Anomaly message")
            teams_message = create_cost_anomaly_message(message_json)
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
