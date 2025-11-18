"""Scraper module for NPbot"""
from .nippon_scraper import NipponScraper
from .validator import DataValidator
from .url_validator import validate_url, normalize_url

__all__ = ["NipponScraper", "DataValidator", "validate_url", "normalize_url"]

