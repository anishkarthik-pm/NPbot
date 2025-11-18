"""Periodic refresh job scheduler for NAV updates and data synchronization"""
import schedule
import time
from datetime import datetime
from typing import Optional

import config
from scraper.nippon_scraper import NipponScraper
from scraper.validator import DataValidator
from storage.data_store import DataStore
from storage.models import SchemeData, FactsheetData


class RefreshScheduler:
    """Manages periodic refresh jobs for mutual fund data"""
    
    def __init__(self):
        self.scraper = NipponScraper()
        self.validator = DataValidator()
        self.data_store = DataStore()
    
    def full_refresh(self):
        """Perform full data refresh (all schemes + factsheets)"""
        print(f"[{datetime.now()}] Starting full refresh...")
        
        try:
            # Scrape all schemes
            print("Scraping all schemes...")
            schemes = self.scraper.scrape_all_schemes()
            
            # Validate and store schemes
            for scheme in schemes:
                if config.VALIDATION_ENABLED:
                    validation_result = self.validator.validate_scheme(scheme)
                    self.validator.update_validation_status(scheme, validation_result)
                
                # Store scheme
                self.data_store.store_scheme(scheme)
                
                # Create and store text chunks
                scheme_text = self._generate_scheme_text(scheme)
                chunks = self.data_store.create_text_chunks(
                    scheme_code=scheme.metadata.scheme_code,
                    content=scheme_text,
                    chunk_type="scheme",
                    source_url=str(scheme.metadata.source_url),
                    metadata={
                        'scheme_name': scheme.metadata.scheme_name,
                        'scheme_type': scheme.metadata.scheme_type
                    }
                )
                self.data_store.store_text_chunks(chunks)
            
            # Scrape factsheets
            print("Scraping factsheets...")
            factsheets = self.scraper.scrape_all_factsheets(schemes)
            
            # Store factsheets
            for factsheet in factsheets:
                self.data_store.store_factsheet(factsheet)
                
                # Create and store text chunks
                chunks = self.data_store.create_text_chunks(
                    scheme_code=factsheet.scheme_code,
                    content=factsheet.raw_text,
                    chunk_type="factsheet",
                    source_url=str(factsheet.source_url),
                    metadata={
                        'scheme_name': factsheet.scheme_name
                    }
                )
                self.data_store.store_text_chunks(chunks)
            
            # Update metadata
            self.data_store.update_refresh_timestamp(nav_only=False)
            
            print(f"[{datetime.now()}] Full refresh completed. Stored {len(schemes)} schemes and {len(factsheets)} factsheets.")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error during full refresh: {e}")
    
    def nav_refresh(self):
        """Perform NAV-only refresh (faster, updates only NAV data)"""
        print(f"[{datetime.now()}] Starting NAV refresh...")
        
        try:
            # Get all stored schemes
            schemes = self.data_store.get_all_schemes()
            
            updated_count = 0
            for scheme in schemes:
                # Re-scrape just the NAV data
                updated_scheme = self.scraper.scrape_scheme_page(
                    str(scheme.metadata.source_url),
                    scheme.metadata.scheme_code
                )
                
                if updated_scheme and updated_scheme.current_nav:
                    # Update NAV data
                    scheme.current_nav = updated_scheme.current_nav
                    scheme.nav_date = updated_scheme.nav_date
                    scheme.nav_data = updated_scheme.nav_data
                    scheme.metadata.last_updated = datetime.now()
                    
                    # Store updated scheme
                    self.data_store.store_scheme(scheme)
                    updated_count += 1
            
            # Update metadata
            self.data_store.update_refresh_timestamp(nav_only=True)
            
            print(f"[{datetime.now()}] NAV refresh completed. Updated {updated_count} schemes.")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error during NAV refresh: {e}")
    
    def _generate_scheme_text(self, scheme: SchemeData) -> str:
        """Generate text representation of scheme data for chunking"""
        text_parts = [
            f"Scheme Name: {scheme.metadata.scheme_name}",
            f"Scheme Code: {scheme.metadata.scheme_code}",
            f"Scheme Type: {scheme.metadata.scheme_type}",
        ]
        
        if scheme.metadata.category:
            text_parts.append(f"Category: {scheme.metadata.category}")
        
        if scheme.current_nav:
            text_parts.append(f"Current NAV: ₹{scheme.current_nav}")
            if scheme.nav_date:
                text_parts.append(f"NAV Date: {scheme.nav_date}")
        
        if scheme.aum:
            text_parts.append(f"AUM: ₹{scheme.aum} Cr")
        
        if scheme.expense_ratio:
            text_parts.append(f"Expense Ratio: {scheme.expense_ratio}%")
        
        if scheme.fund_manager:
            text_parts.append(f"Fund Manager: {scheme.fund_manager}")
        
        if scheme.launch_date:
            text_parts.append(f"Inception Date: {scheme.launch_date}")
        
        if scheme.benchmark:
            text_parts.append(f"Benchmark: {scheme.benchmark}")
        
        if scheme.risk_level:
            text_parts.append(f"Risk Level: {scheme.risk_level}")
        
        if scheme.min_investment:
            text_parts.append(f"Minimum Investment: ₹{scheme.min_investment}")
        
        if scheme.sip_min_investment:
            text_parts.append(f"SIP Minimum: ₹{scheme.sip_min_investment}")
        
        if scheme.performance:
            for period, value in scheme.performance.items():
                text_parts.append(f"{period} Return: {value}%")
        
        if scheme.portfolio:
            text_parts.append(f"Portfolio: {scheme.portfolio}")
        
        return "\n".join(text_parts)
    
    def start_scheduler(self):
        """Start the periodic refresh scheduler"""
        # Schedule daily NAV refresh
        schedule.every().day.at(f"{config.REFRESH_HOUR:02d}:{config.REFRESH_MINUTE:02d}").do(self.nav_refresh)
        
        # Schedule weekly full refresh (Sunday at 2 AM)
        schedule.every().sunday.at(f"{config.REFRESH_HOUR:02d}:{config.REFRESH_MINUTE:02d}").do(self.full_refresh)
        
        print(f"Scheduler started. NAV refresh scheduled daily at {config.REFRESH_HOUR:02d}:{config.REFRESH_MINUTE:02d}")
        print(f"Full refresh scheduled weekly on Sunday at {config.REFRESH_HOUR:02d}:{config.REFRESH_MINUTE:02d}")
        
        # Run scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_once(self, nav_only: bool = False):
        """Run refresh job once (for testing or manual execution)"""
        if nav_only:
            self.nav_refresh()
        else:
            self.full_refresh()

