# Observer Pattern - Booking Event
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class BookingEvent:
    """Event data for booking notifications"""
    user_id: str
    user_name: str
    phone_number: str
    pitch_name: str
    time_slot: str
    location: str
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        # Set timestamp to current time if not provided
        if self.timestamp is None:
            self.timestamp = datetime.now()