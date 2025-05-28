"""Redis-based message queue implementation"""

import json
import asyncio
from typing import Optional, Callable, Dict, Any
import redis.asyncio as redis
from .models import TaskMessage, ResultMessage
from ..config.settings import MessageQueueConfig


class RedisMQ:
    """Redis-based message queue for Raid system"""
    
    def __init__(self, config: MessageQueueConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._subscribers: Dict[str, Callable] = {}
    
    async def connect(self) -> None:
        """Connect to Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True
            )
            # Test connection
            await self.redis_client.ping()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")
    
    async def disconnect(self) -> None:
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def send_task(self, queue_name: str, task: TaskMessage) -> None:
        """Send a task message to a queue"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        message_data = task.model_dump_json()
        await self.redis_client.lpush(queue_name, message_data)
    
    async def receive_task(self, queue_name: str, timeout: int = 0) -> Optional[TaskMessage]:
        """Receive a task message from a queue"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        try:
            result = await self.redis_client.brpop(queue_name, timeout=timeout)
            if result:
                _, message_data = result
                task_dict = json.loads(message_data)
                return TaskMessage(**task_dict)
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to receive task: {e}")
    
    async def send_result(self, queue_name: str, result: ResultMessage) -> None:
        """Send a result message to a queue"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        message_data = result.model_dump_json()
        await self.redis_client.lpush(queue_name, message_data)
    
    async def receive_result(self, queue_name: str, timeout: int = 0) -> Optional[ResultMessage]:
        """Receive a result message from a queue"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        try:
            result = await self.redis_client.brpop(queue_name, timeout=timeout)
            if result:
                _, message_data = result
                result_dict = json.loads(message_data)
                return ResultMessage(**result_dict)
            return None
        except Exception as e:
            raise RuntimeError(f"Failed to receive result: {e}")
    
    async def wait_for_result(
        self, 
        correlation_id: str, 
        result_queue: str,
        timeout: int = 30
    ) -> Optional[ResultMessage]:
        """Wait for a specific result by correlation_id"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > timeout:
                return None
            
            # Check for result with short timeout
            result = await self.receive_result(result_queue, timeout=1)
            if result and result.correlation_id == correlation_id:
                return result
            elif result:
                # Put back result that doesn't match our correlation_id
                await self.send_result(result_queue, result)
            
            await asyncio.sleep(0.1)
    
    def get_task_queue_name(self, profile: str) -> str:
        """Get task queue name for a sub-agent profile"""
        return f"raid:tasks:{profile}"
    
    def get_result_queue_name(self, profile: str) -> str:
        """Get result queue name for a sub-agent profile"""
        return f"raid:results:{profile}"
    
    # Pub/Sub methods for collaboration
    
    async def publish_message(self, channel: str, message: str) -> None:
        """Publish a message to a Redis channel"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        await self.redis_client.publish(channel, message)
    
    async def subscribe_to_channel(self, channel: str, callback: Callable[[str, str], None]) -> None:
        """Subscribe to a Redis channel with a callback"""
        if not self.redis_client:
            raise RuntimeError("Not connected to Redis")
        
        # Create pubsub instance
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        # Store subscription for cleanup
        self._subscribers[channel] = callback
        
        # Start listening task
        asyncio.create_task(self._listen_to_channel(pubsub, channel, callback))
    
    async def _listen_to_channel(self, pubsub, channel: str, callback: Callable[[str, str], None]) -> None:
        """Listen to messages on a subscribed channel"""
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    await callback(message['channel'], message['data'])
        except Exception as e:
            print(f"Error listening to channel {channel}: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    async def unsubscribe_from_channel(self, channel: str) -> None:
        """Unsubscribe from a Redis channel"""
        if channel in self._subscribers:
            del self._subscribers[channel]