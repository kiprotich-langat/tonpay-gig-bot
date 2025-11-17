import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path="tonpay.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = None
        
    def get_connection(self):
        """Get database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                wallet_address TEXT,
                rating REAL DEFAULT 0,
                total_earned REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        #gigs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gigs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                status TEXT DEFAULT 'open',
                escrow_address TEXT,
                freelancer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES users(id),
                FOREIGN KEY (freelancer_id) REFERENCES users(id)
            )
        """)
        
        # applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gig_id INTEGER NOT NULL,
                freelancer_id INTEGER NOT NULL,
                proposal TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gig_id) REFERENCES gigs(id),
                FOREIGN KEY (freelancer_id) REFERENCES users(id),
                UNIQUE(gig_id, freelancer_id)
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gig_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                tx_hash TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gig_id) REFERENCES gigs(id),
                FOREIGN KEY (from_user_id) REFERENCES users(id),
                FOREIGN KEY (to_user_id) REFERENCES users(id)
            )
        """)
        
        # rating table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gig_id INTEGER NOT NULL,
                from_user_id INTEGER NOT NULL,
                to_user_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gig_id) REFERENCES gigs(id),
                FOREIGN KEY (from_user_id) REFERENCES users(id),
                FOREIGN KEY (to_user_id) REFERENCES users(id)
            )
        """)
        
        # disputes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disputes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gig_id INTEGER NOT NULL,
                raised_by INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                FOREIGN KEY (gig_id) REFERENCES gigs(id),
                FOREIGN KEY (raised_by) REFERENCES users(id)
            )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully")
    
    #user operations
    def add_user(self, user_id: int, username: str) -> bool:
        """Add a new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (user_id, username)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"User {user_id} already exists")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_user_wallet(self, user_id: int, wallet_address: str) -> bool:
        """Update user's wallet address"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET wallet_address = ? WHERE id = ?",
                (wallet_address, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating wallet: {e}")
            return False
    
    def update_user_rating(self, user_id: int, new_rating: float) -> bool:
        """Update user's rating"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET rating = ? WHERE id = ?",
                (new_rating, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating rating: {e}")
            return False
    
    #Gig operations
    def create_gig(self, client_id: int, title: str, description: str, price: float) -> int:
        """Create a new gig"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO gigs (client_id, title, description, price)
               VALUES (?, ?, ?, ?)""",
            (client_id, title, description, price)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_gig(self, gig_id: int) -> Optional[Dict]:
        """Get gig by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM gigs WHERE id = ?", (gig_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_open_gigs(self, limit: int = 50) -> List[Dict]:
        """Get all open gigs"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM gigs 
               WHERE status = 'open' 
               ORDER BY created_at DESC 
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_gigs(self, user_id: int) -> List[Dict]:
        """Get all gigs posted by a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM gigs 
               WHERE client_id = ? 
               ORDER BY created_at DESC""",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def update_gig_status(self, gig_id: int, status: str, freelancer_id: Optional[int] = None) -> bool:
        """Update gig status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if freelancer_id:
                cursor.execute(
                    "UPDATE gigs SET status = ?, freelancer_id = ? WHERE id = ?",
                    (status, freelancer_id, gig_id)
                )
            else:
                cursor.execute(
                    "UPDATE gigs SET status = ? WHERE id = ?",
                    (status, gig_id)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating gig status: {e}")
            return False
    
    def update_gig_escrow(self, gig_id: int, escrow_address: str) -> bool:
        """Update gig's escrow address"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE gigs SET escrow_address = ? WHERE id = ?",
                (escrow_address, gig_id)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating escrow address: {e}")
            return False
    
    def complete_gig(self, gig_id: int) -> bool:
        """Mark gig as completed"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE gigs 
                   SET status = 'completed', completed_at = CURRENT_TIMESTAMP 
                   WHERE id = ?""",
                (gig_id,)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error completing gig: {e}")
            return False
    
    #application operations
    def create_application(self, gig_id: int, freelancer_id: int, proposal: str) -> int:
        """Create a new application"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO applications (gig_id, freelancer_id, proposal)
               VALUES (?, ?, ?)""",
            (gig_id, freelancer_id, proposal)
        )
        conn.commit()
        return cursor.lastrowid
    
    def get_application(self, app_id: int) -> Optional[Dict]:
        """Get application by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_gig_applications(self, gig_id: int) -> List[Dict]:
        """Get all applications for a gig"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT * FROM applications 
               WHERE gig_id = ? 
               ORDER BY created_at DESC""",
            (gig_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_applications(self, user_id: int) -> List[Dict]:
        """Get all applications by a user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """SELECT a.*, g.title, g.price, g.status as gig_status
               FROM applications a
               JOIN gigs g ON a.gig_id = g.id
               WHERE a.freelancer_id = ? 
               ORDER BY a.created_at DESC""",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def count_applications(self, gig_id: int) -> int:
        """Count applications for a gig"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM applications WHERE gig_id = ?",
            (gig_id,)
        )
        return cursor.fetchone()[0]
    
    def has_applied(self, user_id: int, gig_id: int) -> bool:
        """Check if user has already applied to a gig"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM applications WHERE freelancer_id = ? AND gig_id = ?",
            (user_id, gig_id)
        )
        return cursor.fetchone()[0] > 0
    
    def accept_application(self, app_id: int) -> bool:
        """Accept an application"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get application details
            app = self.get_application(app_id)
            if not app:
                return False
            
            cursor.execute(
                "UPDATE applications SET status = 'accepted' WHERE id = ?",
                (app_id,)
            )
            
            cursor.execute(
                """UPDATE gigs 
                   SET status = 'in_progress', freelancer_id = ? 
                   WHERE id = ?""",
                (app['freelancer_id'], app['gig_id'])
            )
    
            cursor.execute(
                """UPDATE applications 
                   SET status = 'rejected' 
                   WHERE gig_id = ? AND id != ?""",
                (app['gig_id'], app_id)
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error accepting application: {e}")
            return False
    
    #transaction operations
    def create_transaction(self, gig_id: int, from_user: int, to_user: int, 
                          amount: float, tx_hash: Optional[str] = None) -> int:
        """Create a new transaction record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO transactions 
               (gig_id, from_user_id, to_user_id, amount, tx_hash)
               VALUES (?, ?, ?, ?, ?)""",
            (gig_id, from_user, to_user, amount, tx_hash)
        )
        conn.commit()
        return cursor.lastrowid
    
    def update_transaction_status(self, tx_id: int, status: str, tx_hash: Optional[str] = None) -> bool:
        """Update transaction status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            if tx_hash:
                cursor.execute(
                    "UPDATE transactions SET status = ?, tx_hash = ? WHERE id = ?",
                    (status, tx_hash, tx_id)
                )
            else:
                cursor.execute(
                    "UPDATE transactions SET status = ? WHERE id = ?",
                    (status, tx_id)
                )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    #rating operations
    def add_rating(self, gig_id: int, from_user: int, to_user: int, 
                   rating: int, comment: Optional[str] = None) -> int:
        """Add a rating"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO ratings 
               (gig_id, from_user_id, to_user_id, rating, comment)
               VALUES (?, ?, ?, ?, ?)""",
            (gig_id, from_user, to_user, rating, comment)
        )
        conn.commit()
        
        #updte user's average rating
        self._update_user_average_rating(to_user)
        
        return cursor.lastrowid
    
    def _update_user_average_rating(self, user_id: int):
        """Update user's average rating"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT AVG(rating) FROM ratings WHERE to_user_id = ?",
            (user_id,)
        )
        avg_rating = cursor.fetchone()[0] or 0
        self.update_user_rating(user_id, round(avg_rating, 1))
    
    #dispute operations
    def create_dispute(self, gig_id: int, raised_by: int, reason: str) -> int:
        """Create a dispute"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO disputes (gig_id, raised_by, reason)
               VALUES (?, ?, ?)""",
            (gig_id, raised_by, reason)
        )
        conn.commit()
        
        #Update gig status
        self.update_gig_status(gig_id, 'disputed')
        
        return cursor.lastrowid
    
    def get_dispute(self, dispute_id: int) -> Optional[Dict]:
        """Get dispute by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM disputes WHERE id = ?", (dispute_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_gig_disputes(self, gig_id: int) -> List[Dict]:
        """Get all disputes for a gig"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM disputes WHERE gig_id = ? ORDER BY created_at DESC",
            (gig_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    #Statistics
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        

        cursor.execute(
            "SELECT COUNT(*) FROM gigs WHERE client_id = ?",
            (user_id,)
        )
        gigs_posted = cursor.fetchone()[0]
        
        cursor.execute(
            "SELECT COUNT(*) FROM gigs WHERE client_id = ? AND status = 'completed'",
            (user_id,)
        )
        gigs_completed_client = cursor.fetchone()[0]
        

        cursor.execute(
            "SELECT COUNT(*) FROM gigs WHERE freelancer_id = ? AND status = 'completed'",
            (user_id,)
        )
        jobs_completed_freelancer = cursor.fetchone()[0]

        user = self.get_user(user_id)
        
        return {
            'gigs_posted': gigs_posted,
            'gigs_completed_client': gigs_completed_client,
            'jobs_completed_freelancer': jobs_completed_freelancer,
            'total_earned': user.get('total_earned', 0),
            'total_spent': user.get('total_spent', 0)
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

            self.conn = None
