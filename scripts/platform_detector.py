#!/usr/bin/python
"""
Platform detection module for TestFlight links.
Lightweight implementation optimized for GitHub Actions environment.

Detects supported platforms by analyzing TestFlight page content.
Includes graceful fallback if detection fails.
"""
import re
from typing import Set, Optional

# Simple keyword patterns for each platform
# These are more specific to avoid false positives
PLATFORM_KEYWORDS = {
    'ios': [
        'requires ios', 'iphone', 'compatible with iphone',
    ],
    'ipados': [
        'ipad', 'requires ipados', 'compatible with ipad',
    ],
    'macos': [
        'requires macos', 'mac app', 'compatible with mac',
    ],
    'tvos': [
        'requires tvos', 'apple tv', 'compatible with apple tv',
    ],
}

def detect_platforms(html_content: str) -> Set[str]:
    """
    Detect supported platforms from TestFlight HTML content.
    
    This is a lightweight implementation that searches for simple keywords.
    If detection fails gracefully, it returns an empty set and let caller
    decide the default behavior.
    
    Args:
        html_content: HTML content from TestFlight page
        
    Returns:
        Set of detected platforms: {'ios', 'ipados', 'macos', 'tvos'}
        Returns empty set if detection fails or no keywords found
    """
    if not html_content or not isinstance(html_content, str):
        return set()
    
    detected = set()
    html_lower = html_content.lower()
    
    try:
        # Simple keyword matching
        for platform, keywords in PLATFORM_KEYWORDS.items():
            for keyword in keywords:
                if keyword in html_lower:
                    detected.add(platform)
                    break
        
        return detected
        
    except Exception as e:
        # Graceful failure in case of any parsing error
        print(f"[warn] Platform detection failed: {e}")
        return set()
