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
# These are lightweight and don't require complex parsing
PLATFORM_KEYWORDS = {
    'ios': [
        'iphone', 'ios', 'requires ios',
    ],
    'macos': [
        'macos', 'mac app', 'requires macos', 'mac compatible',
    ],
    'tvos': [
        'tvos', 'apple tv', 'tv app', 'requires tvos',
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
        Set of detected platforms: {'ios', 'macos', 'tvos'}
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
        
        # Basic validation: if we found nothing, return empty
        # Caller should decide what to do
        return detected
        
    except Exception as e:
        # Graceful failure in case of any parsing error
        print(f"[warn] Platform detection failed: {e}")
        return set()


def get_recommended_categories(platforms: Optional[Set[str]]) -> list:
    """
    Map detected platforms to app categories.
    
    Args:
        platforms: Set of detected platforms, or None
        
    Returns:
        List of recommended categories, or empty list if no platforms detected
    """
    if not platforms:
        return []
    
    # Platform to category mapping
    platform_to_category = {
        'ios': 'ios',
        'macos': 'macos',
        'tvos': 'tvos',
    }
    
    categories = []
    
    # Map platforms to categories in priority order
    for platform in ['ios', 'macos', 'tvos']:
        if platform in platforms:
            category = platform_to_category[platform]
            if category not in categories:
                categories.append(category)
    
    return categories


# Test example
if __name__ == "__main__":
    # Test with a sample HTML
    test_html = """
    <html>
    <title>Join the MyApp beta - TestFlight - Apple</title>
    <body>
    MyApp requires iOS 14.0 or later
    Compatible with iPhone, iPad, Mac, and Apple Watch
    </body>
    </html>
    """
    
    platforms = detect_platforms(test_html)
    categories = get_recommended_categories(platforms)
    
    print(f"Detected platforms: {platforms}")
    print(f"Recommended categories: {categories}")

