#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import get_sync_db
from app.db.models import User, Subscription, Source, Language

def debug_subscriptions():
    """Debug function to check subscriptions in database"""
    db = get_sync_db()
    try:
        print("=== DEBUGGING SUBSCRIPTIONS ===")
        
        # Check all users
        users = db.query(User).all()
        print(f"Total users in database: {len(users)}")
        
        for user in users:
            print(f"\nUser: {user.id} (telegram_id: {user.telegram_id})")
            print(f"Subscriptions count: {len(user.subscriptions)}")
            
            for sub in user.subscriptions:
                source = db.query(Source).filter(Source.id == sub.source_id).first()
                source_name = source.name if source else "Unknown"
                print(f"  - Subscription {sub.id}: active={sub.is_active}, source={source_name} ({sub.language})")
        
        # Check all subscriptions directly
        print(f"\n=== ALL SUBSCRIPTIONS ===")
        all_subs = db.query(Subscription).all()
        print(f"Total subscriptions in database: {len(all_subs)}")
        
        for sub in all_subs:
            user = db.query(User).filter(User.id == sub.user_id).first()
            source = db.query(Source).filter(Source.id == sub.source_id).first()
            user_telegram = user.telegram_id if user else "Unknown"
            source_name = source.name if source else "Unknown"
            print(f"  - {sub.id}: user={user_telegram}, source={source_name}, active={sub.is_active}")
            
    finally:
        db.close()

if __name__ == "__main__":
    debug_subscriptions() 