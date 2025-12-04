# Push Notification Service
import json
from typing import Optional
from pywebpush import webpush, WebPushException
from app.features.messages.models import PushSubscription
from app.core.logging import logger
from app.config import settings


class PushNotificationService:
    """Service for sending push notifications."""
    
    @staticmethod
    def get_vapid_credentials():
        """Get VAPID credentials from settings."""
        public_key = settings.VAPID_PUBLIC_KEY
        private_key = settings.VAPID_PRIVATE_KEY
        
        if not public_key or not private_key:
            logger.warning("⚠️ VAPID keys not configured. Push notifications will not work.")
            return None, None
        
        return public_key, private_key
    
    @staticmethod
    async def send_push_notification(
        subscription: PushSubscription,
        title: str,
        body: str,
        data: Optional[dict] = None
    ) -> bool:
        """
        Send a push notification to a subscription.
        
        Args:
            subscription: PushSubscription model instance
            title: Notification title
            body: Notification body
            data: Optional additional data
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            public_key, private_key = PushNotificationService.get_vapid_credentials()
            if not public_key or not private_key:
                return False
            
            # Prepare subscription info
            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth
                }
            }
            
            # Prepare notification payload
            payload = {
                "title": title,
                "body": body,
                "icon": "/icon.svg",
                "badge": "/icon.svg",
                "tag": data.get("tag", "message") if data else "message",
                "data": data or {}
            }
            
            # Send push notification
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload),
                vapid_private_key=private_key,
                vapid_claims={
                    "sub": "mailto:saeedanwar@getsnippet.co"  # Contact email for VAPID
                }
            )
            
            logger.info(f"✅ Push notification sent to {subscription.subscription_type} {subscription.user_id or subscription.patient_id}")
            return True
            
        except WebPushException as e:
            logger.error(f"❌ WebPush error: {e}")
            # If subscription is invalid, mark it as inactive
            if e.response and e.response.status_code in [410, 404]:
                subscription.is_active = False
                await subscription.save()
                logger.info(f"Marked subscription as inactive due to {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to send push notification: {e}")
            return False
    
    @staticmethod
    async def send_message_notification(
        recipient_type: str,
        recipient_id: str,
        sender_name: str,
        message_content: str,
        conversation_id: str
    ) -> bool:
        """
        Send a push notification for a new message.
        
        Args:
            recipient_type: "doctor" or "patient"
            recipient_id: user_id for doctor, patient_id for patient
            sender_name: Name of the message sender
            message_content: Content of the message
            conversation_id: ID of the conversation
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Find active subscription for recipient
            if recipient_type == "doctor":
                subscriptions = await PushSubscription.find(
                    {"user_id": recipient_id, "is_active": True}
                ).to_list()
            else:
                subscriptions = await PushSubscription.find(
                    {"patient_id": recipient_id, "is_active": True}
                ).to_list()
            
            if not subscriptions:
                logger.debug(f"No active push subscription found for {recipient_type} {recipient_id}")
                return False
            
            # Send notification to all active subscriptions (user might have multiple devices)
            success_count = 0
            for subscription in subscriptions:
                # Check if recipient has notifications enabled
                if recipient_type == "doctor":
                    from app.features.auth.models import User
                    from bson import ObjectId
                    try:
                        user = await User.get(ObjectId(subscription.user_id))
                        if not user or not user.notifications_enabled:
                            continue
                    except Exception:
                        continue
                else:
                    from app.features.patients.models import Patient
                    if not subscription.patient_id:
                        continue
                    patient = await Patient.find_one(Patient.patient_id == subscription.patient_id)
                    if not patient or not patient.notifications_enabled:
                        continue
                
                # Truncate message if too long
                truncated_content = message_content[:100] + "..." if len(message_content) > 100 else message_content
                
                success = await PushNotificationService.send_push_notification(
                    subscription=subscription,
                    title=f"New message from {sender_name}",
                    body=truncated_content,
                    data={
                        "type": "message",
                        "conversation_id": conversation_id,
                        "sender_name": sender_name,
                        "url": "/messages"
                    }
                )
                
                if success:
                    success_count += 1
            
            logger.info(f"📱 Sent push notifications to {success_count}/{len(subscriptions)} subscriptions for {recipient_type} {recipient_id}")
            return success_count > 0
            
        except Exception as e:
            import traceback
            logger.error(f"❌ Failed to send message notification: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

