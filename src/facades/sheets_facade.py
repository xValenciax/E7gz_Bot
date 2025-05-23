# Facade Pattern - Google Sheets Facade
import logging
from typing import Dict, List, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class SheetsFacade:
    """Facade for Google Sheets operations"""
    def __init__(self, credentials_file, scopes, sheet_name=None, sheet_id=None):
        self.credentials_file = credentials_file
        self.scopes = scopes
        self.sheet_name = sheet_name
        self.sheet_id = sheet_id
        self.logger = logging.getLogger('telegram_bot')
        self.workbook = None
        self.pitches_sheet = None
        self.bookings_sheet = None
        self.initialize_connection()

    def initialize_connection(self):
        """Initialize connection to Google Sheets"""
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file,
                self.scopes
            )
            gc = gspread.authorize(credentials)
            
            # Try to open by ID first if provided, otherwise use name
            if self.sheet_id:
                try:
                    self.workbook = gc.open_by_key(self.sheet_id)
                    self.logger.info(f'Opened workbook by ID: {self.sheet_id}')
                except Exception as e:
                    self.logger.error(f'Could not open workbook with ID: {self.sheet_id}. Error: {str(e)}')
                    raise
            else:
                try:
                    self.workbook = gc.open(self.sheet_name)
                    self.logger.info(f'Opened workbook by name: {self.sheet_name}')
                except gspread.exceptions.SpreadsheetNotFound:
                    self.logger.error(f'Could not open workbook with name: {self.sheet_name}')
                    self.logger.error('Make sure the workbook exists and is shared with the service account email')
                    raise
            
            self._initialize_worksheets()
            self.logger.info('Successfully connected to Google Sheets')
        except Exception as e:
            self.logger.error(f'Failed to connect to Google Sheets: {str(e)}')
            raise

    def _initialize_worksheets(self):
        """Initialize or create required worksheets"""
        try:
            self.pitches_sheet = self.workbook.worksheet('Pitches')
            self.logger.info('Accessed Pitches worksheet')
        except gspread.exceptions.WorksheetNotFound:
            # Create Pitches worksheet with headers if it doesn't exist
            self.pitches_sheet = self.workbook.add_worksheet(title='Pitches', rows=100, cols=20)
            self.pitches_sheet.append_row(['Location', 'Pitch Name', 'Time Slots', 'Owner Phone'])
            self.logger.info('Created new Pitches worksheet')
        
        try:
            self.bookings_sheet = self.workbook.worksheet('Bookings')
            self.logger.info('Accessed Bookings worksheet')
            
            # Check if the Bookings sheet has the required columns
            headers = self.bookings_sheet.row_values(1)
            if 'Phone Number' not in headers or 'User Name' not in headers:
                # Add the new columns if they don't exist
                if 'Phone Number' not in headers:
                    self.bookings_sheet.append_col(['Phone Number'] + [''] * (len(self.bookings_sheet.col_values(1)) - 1))
                    self.logger.info('Added Phone Number column to Bookings worksheet')
                if 'User Name' not in headers:
                    self.bookings_sheet.append_col(['User Name'] + [''] * (len(self.bookings_sheet.col_values(1)) - 1))
                    self.logger.info('Added User Name column to Bookings worksheet')
        except gspread.exceptions.WorksheetNotFound:
            # Create Bookings worksheet with headers if it doesn't exist
            self.bookings_sheet = self.workbook.add_worksheet(title='Bookings', rows=100, cols=20)
            self.bookings_sheet.append_row(['User ID', 'Pitch Name', 'Date/Time', 'Status', 'Phone Number', 'User Name'])
            self.logger.info('Created new Bookings worksheet')

    def get_unique_locations(self) -> List[str]:
        """Get unique locations from the Pitches sheet"""
        all_pitches = self.pitches_sheet.get_all_records()
        return sorted(set(pitch['Location'] for pitch in all_pitches))

    def get_pitches_by_location(self, location: str) -> List[Dict]:
        """Get pitches for a specific location"""
        all_pitches = self.pitches_sheet.get_all_records()
        return [pitch for pitch in all_pitches if pitch['Location'] == location]

    def get_available_time_slots(self, pitch_name: str) -> List[str]:
        """Get available time slots for a specific pitch"""
        # Get all time slots for the pitch
        all_pitches = self.pitches_sheet.get_all_records()
        pitch_data = next((pitch for pitch in all_pitches if pitch['Pitch Name'] == pitch_name), None)
        
        if not pitch_data:
            return []
        
        available_slots = [slot.strip() for slot in pitch_data['Time Slots'].split(',')]
        
        # Check which slots are already booked
        bookings = self.bookings_sheet.get_all_records()
        booked_slots = [booking['Date/Time'] for booking in bookings 
                       if booking['Status'] == 'Booked' and booking['Pitch Name'] == pitch_name]
        
        # Remove booked slots from available slots
        return [slot for slot in available_slots if slot not in booked_slots]

    def is_slot_available(self, pitch_name: str, time_slot: str) -> bool:
        """Check if a specific time slot is available for a pitch"""
        bookings = self.bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] == pitch_name):
                return False
        return True

    def add_booking(self, user_id: str, user_name: str, phone_number: str, 
                   pitch_name: str, time_slot: str, status: str = 'Booked') -> bool:
        """Add a new booking to the Bookings sheet"""
        try:
            self.bookings_sheet.append_row([
                user_id, 
                user_name,
                phone_number,
                pitch_name, 
                time_slot, 
                status
            ])
            return True
        except Exception as e:
            self.logger.error(f'Error adding booking: {str(e)}')
            return False