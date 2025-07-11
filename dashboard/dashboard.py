from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import mysql.connector
from mysql.connector import pooling
import os

app = FastAPI()

# Database configuration
db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "dashboard"),
    "pool_name": "crawler_pool",
    "pool_size": 5
}

# Create connection pool
connection_pool = pooling.MySQLConnectionPool(**db_config)

def get_db_connection():
    try:
        connection = connection_pool.get_connection()
        yield connection
    finally:
        connection.close()

# Request/Response Models
class Pagination(BaseModel):
    page_num: Optional[int] = 1
    page_size: Optional[int] = 10

class CrawlerGridRequest(BaseModel):
    pagination: Optional[Pagination] = None
    keyword: Optional[str] = None

class ModifyCrawlerRequest(BaseModel):
    id: int
    alias: Optional[str] = None
    max_browser_count: Optional[int] = None

class SessionGridRequest(BaseModel):
    pagination: Optional[Pagination] = None
    keyword: Optional[str] = None
    crawler_id: Optional[int] = None
    session_id: Optional[int] = None

class LogGridRequest(BaseModel):
    pagination: Optional[Pagination] = None
    keyword: Optional[str] = None
    crawler_id: Optional[int] = None
    session_id: Optional[int] = None

class BaseResponse(BaseModel):
    total: int
    rows: List[dict]

# Helper functions
def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None

def apply_pagination(query: str, params: list, pagination: Optional[Pagination] = None) -> tuple:
    if pagination is None:
        pagination = Pagination()
    
    # Ensure page_num and page_size are not None
    page_num = pagination.page_num or 1
    page_size = pagination.page_size or 10
    
    offset = (page_num - 1) * page_size
    query += " LIMIT %s OFFSET %s"
    params.extend([page_size, offset])
    return query, params

# API Endpoints
@app.post("/crawler/grid", response_model=BaseResponse)
def crawler_grid(request: CrawlerGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # 修正表别名使用 - 确保与JOIN语句中的别名一致
        query = """
        SELECT ci.id, cstat.host_name, ci.alias,ci.max_browser_count, cstat.ip, cstat.os, cstat.agent, 
               cstat.last_heartbeat, cstat.status
        FROM crawler_info ci
        JOIN crawler_status cstat ON ci.id = cstat.crawler_id
        """
        
        count_query = """
        SELECT COUNT(*) as total
        FROM crawler_info ci
        JOIN crawler_status cstat ON ci.id = cstat.crawler_id
        """
        
        # Build WHERE clause for crawler grid
        conditions = []
        params = []
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(ci.alias LIKE %s OR cstat.host_name LIKE %s OR cstat.ip LIKE %s)")
            params.extend([like_value, like_value, like_value])
        
        if conditions:
            where_clause = " AND ".join(conditions)
            query += " WHERE " + where_clause
            count_query += " WHERE " + where_clause
        
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        query, params = apply_pagination(query, params, request.pagination)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        rows = []
        for row in results:
            row['last_heartbeat'] = format_datetime(row['last_heartbeat'])
            rows.append(row)
        
        return {"total": total, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()

@app.post("/crawler/modify")
def modify_crawler(request: ModifyCrawlerRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        db.start_transaction()
        cursor = db.cursor(dictionary=True)
        
        # Build update query
        update_fields = []
        params = []
        if request.alias is not None:
            update_fields.append("alias = %s")
            params.append(request.alias)
        if request.max_browser_count is not None:
            update_fields.append("max_browser_count = %s")
            params.append(request.max_browser_count)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        update_query = f"""
        UPDATE crawler_info 
        SET {", ".join(update_fields)}
        WHERE id = %s
        """
        params.append(request.id)
        
        cursor.execute(update_query, params)
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Crawler not found")
        
        # Get updated crawler info
        select_query = """
        SELECT ci.id, cs.host_name, ci.alias, cs.ip, cs.os, cs.agent, 
               cs.last_heartbeat, cs.status
        FROM crawler_info ci
        JOIN crawler_status cs ON ci.id = cs.crawler_id
        WHERE ci.id = %s
        """
        cursor.execute(select_query, (request.id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Crawler status not found")
        
        db.commit()
        
        # Format datetime field
        result['last_heartbeat'] = format_datetime(result['last_heartbeat'])
        
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()

@app.post("/session/grid", response_model=BaseResponse)
def session_grid(request: SessionGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # Base query
        query = """
        SELECT csess.id, ci.alias, cstat.host_name, cstat.ip, csess.session_id, 
               csess.url, csess.init_time, csess.destroy_time
        FROM crawler_session csess
        JOIN crawler_info ci ON csess.crawler_id = ci.id
        JOIN crawler_status cstat ON csess.crawler_id = cstat.crawler_id
        """
        
        # Count query
        count_query = """
        SELECT COUNT(*) as total
        FROM crawler_session csess
        JOIN crawler_info ci ON csess.crawler_id = ci.id
        JOIN crawler_status cstat ON csess.crawler_id = cstat.crawler_id
        """
        
        # Build WHERE clause for session grid
        conditions = []
        params = []
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(ci.alias LIKE %s OR cstat.host_name LIKE %s OR cstat.ip LIKE %s OR csess.session_id LIKE %s)")
            params.extend([like_value, like_value, like_value, like_value])
        if request.crawler_id:
            conditions.append("csess.crawler_id = %s")
            params.append(request.crawler_id)
        if request.session_id:
            conditions.append("csess.id = %s")
            params.append(request.session_id)
        
        if conditions:
            where_clause = " AND ".join(conditions)
            query += " WHERE " + where_clause
            count_query += " WHERE " + where_clause
        
        # Get total count
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        query, params = apply_pagination(query, params, request.pagination)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format datetime fields
        rows = []
        for row in results:
            row['init_time'] = format_datetime(row['init_time'])
            row['destroy_time'] = format_datetime(row['destroy_time'])
            rows.append(row)
        
        return {"total": total, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()

@app.post("/log/grid", response_model=BaseResponse)
def log_grid(request: LogGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # Base query
        query = """
        SELECT al.id, ci.alias, cstat.host_name, cstat.ip, csess.session_id, 
               al.api, al.request_time, al.response_time, al.status_code
        FROM api_log al
        JOIN crawler_session csess ON al.crawler_session_id = csess.id
        JOIN crawler_info ci ON csess.crawler_id = ci.id
        JOIN crawler_status cstat ON csess.crawler_id = cstat.crawler_id
        """
        
        # Count query
        count_query = """
        SELECT COUNT(*) as total
        FROM api_log al
        JOIN crawler_session csess ON al.crawler_session_id = csess.id
        JOIN crawler_info ci ON csess.crawler_id = ci.id
        JOIN crawler_status cstat ON csess.crawler_id = cstat.crawler_id
        """
        
        # Build WHERE clause for log grid
        conditions = []
        params = []
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(ci.alias LIKE %s OR cstat.host_name LIKE %s OR cstat.ip LIKE %s OR csess.session_id LIKE %s OR al.api LIKE %s)")
            params.extend([like_value, like_value, like_value, like_value, like_value])
        if request.crawler_id:
            conditions.append("csess.crawler_id = %s")
            params.append(request.crawler_id)
        if request.session_id:
            conditions.append("al.crawler_session_id = %s")
            params.append(request.session_id)
        
        if conditions:
            where_clause = " AND ".join(conditions)
            query += " WHERE " + where_clause
            count_query += " WHERE " + where_clause
        
        # Get total count
        cursor.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Apply pagination
        query, params = apply_pagination(query, params, request.pagination)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format datetime fields
        rows = []
        for row in results:
            row['request_time'] = format_datetime(row['request_time'])
            row['response_time'] = format_datetime(row['response_time'])
            rows.append(row)
        
        return {"total": total, "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)