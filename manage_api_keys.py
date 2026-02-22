#!/usr/bin/env python
"""
CLI utility for managing API keys.

Usage:
    python manage_api_keys.py create --name "My App" --role admin
    python manage_api_keys.py list
    python manage_api_keys.py deactivate --id 1
"""

import argparse
import asyncio
import sys
from datetime import datetime

from sqlalchemy import select

from app.crud.api_key import (
    create_api_key,
    deactivate_api_key,
    list_api_keys,
)
from app.database import AsyncSessionLocal
from app.models.api_key import APIKey, APIKeyRole


async def create_key(args):
    """Create a new API key"""
    async with AsyncSessionLocal() as db:
        try:
            role = APIKeyRole(args.role)
        except ValueError:
            print(f"Error: Invalid role '{args.role}'")
            print(f"Valid roles: {', '.join([r.value for r in APIKeyRole])}")
            return 1
        
        api_key = await create_api_key(
            db=db,
            name=args.name,
            role=role,
            description=args.description,
            rate_limit_requests=args.rate_limit,
            rate_limit_period=args.rate_period,
            expires_in_days=args.expires_in_days,
        )
        
        print("\n✅ API Key created successfully!")
        print(f"\nID: {api_key.id}")
        print(f"Name: {api_key.name}")
        print(f"Role: {api_key.role}")
        print(f"Rate Limit: {api_key.rate_limit_requests} requests per {api_key.rate_limit_period}s")
        print(f"\n🔑 API Key: {api_key.key}")
        print("\n⚠️  IMPORTANT: Save this key securely! It won't be shown again.")
        
        if api_key.expires_at:
            print(f"\n⏰ Expires: {api_key.expires_at}")
        
        return 0


async def list_keys(args):
    """List all API keys"""
    async with AsyncSessionLocal() as db:
        keys = await list_api_keys(db, skip=0, limit=1000)
        
        if not keys:
            print("No API keys found.")
            return 0
        
        print(f"\n📋 Found {len(keys)} API key(s):\n")
        print(f"{'ID':<5} {'Name':<20} {'Role':<10} {'Active':<8} {'Last Used':<20} {'Expires':<20}")
        print("-" * 90)
        
        for key in keys:
            last_used = key.last_used_at.strftime("%Y-%m-%d %H:%M") if key.last_used_at else "Never"
            expires = key.expires_at.strftime("%Y-%m-%d %H:%M") if key.expires_at else "Never"
            active = "✓" if key.is_active else "✗"
            
            # Mark expired keys
            if key.is_expired():
                expires = f"{expires} (EXPIRED)"
            
            print(f"{key.id:<5} {key.name:<20} {key.role:<10} {active:<8} {last_used:<20} {expires:<20}")
        
        return 0


async def deactivate_key(args):
    """Deactivate an API key"""
    async with AsyncSessionLocal() as db:
        success = await deactivate_api_key(db, args.id)
        
        if success:
            print(f"✅ API key {args.id} deactivated successfully.")
            return 0
        else:
            print(f"❌ API key {args.id} not found.")
            return 1


async def show_key_info(args):
    """Show detailed information about an API key"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(APIKey).where(APIKey.id == args.id)
        )
        key = result.scalar_one_or_none()
        
        if not key:
            print(f"❌ API key {args.id} not found.")
            return 1
        
        print(f"\n📋 API Key Details:\n")
        print(f"ID: {key.id}")
        print(f"Name: {key.name}")
        print(f"Description: {key.description or 'N/A'}")
        print(f"Role: {key.role}")
        print(f"Active: {'Yes' if key.is_active else 'No'}")
        print(f"Rate Limit: {key.rate_limit_requests} requests per {key.rate_limit_period}s")
        print(f"Created: {key.created_at}")
        print(f"Last Used: {key.last_used_at or 'Never'}")
        print(f"Expires: {key.expires_at or 'Never'}")
        
        if key.is_expired():
            print("\n⚠️  This key is EXPIRED")
        elif not key.is_active:
            print("\n⚠️  This key is INACTIVE")
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage VoltWay API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("--name", required=True, help="Name for the API key")
    create_parser.add_argument(
        "--role",
        choices=["admin", "user", "readonly"],
        default="user",
        help="Role for the API key (default: user)",
    )
    create_parser.add_argument("--description", help="Description for the API key")
    create_parser.add_argument(
        "--rate-limit",
        type=int,
        default=100,
        help="Rate limit requests (default: 100)",
    )
    create_parser.add_argument(
        "--rate-period",
        type=int,
        default=60,
        help="Rate limit period in seconds (default: 60)",
    )
    create_parser.add_argument(
        "--expires-in-days",
        type=int,
        help="Expiration in days (optional)",
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all API keys")
    
    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate an API key")
    deactivate_parser.add_argument("--id", type=int, required=True, help="API key ID")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Show API key details")
    info_parser.add_argument("--id", type=int, required=True, help="API key ID")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == "create":
        return asyncio.run(create_key(args))
    elif args.command == "list":
        return asyncio.run(list_keys(args))
    elif args.command == "deactivate":
        return asyncio.run(deactivate_key(args))
    elif args.command == "info":
        return asyncio.run(show_key_info(args))
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
