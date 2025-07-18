#
# pip install fastapi uvicorn[standard] pydantic mysql-connector-python
#
from fastapi import FastAPI, HTTPException, Depends, Body
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

class LogGridRequest(BaseModel):
    pagination: Optional[Pagination] = None
    keyword: Optional[str] = None
    session_id: Optional[int] = None

class PageResponse(BaseModel):
    total: int
    rows: List[dict]

class DeleteRequest(BaseModel):
    ids: List[int]

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
@app.post("/crawler/grid", response_model=PageResponse)
def crawler_grid(request: CrawlerGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # /crawler/grid
        query = """
        SELECT ci.id, ci.uuid, ci.host_name, ci.external_ip, ci.internal_ip,
               ci.os, ci.agent, ci.last_heartbeat, ci.status, ci.cpu_usage,
               ci.memory_usage, ci.create_time, ci.update_time,
               cset.alias, cset.max_browser_count
        FROM crawler_info ci
        LEFT JOIN crawler_setting cset ON cset.crawler_id = ci.id
        """
        
        count_query = """
        SELECT COUNT(*) as total
        FROM crawler_info ci
        LEFT JOIN crawler_setting cset ON cset.crawler_id = ci.id
        """
        
        # Build WHERE clause for crawler grid
        conditions = []
        params = []
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(ci.uuid LIKE %s OR ci.host_name LIKE %s OR ci.internal_ip LIKE %s OR ci.external_ip LIKE %s OR cset.alias LIKE %s)")
            params.extend([like_value, like_value, like_value, like_value, like_value])
        
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
        UPDATE crawler_setting 
        SET {", ".join(update_fields)}
        WHERE id = %s
        """
        params.append(request.id)
        
        cursor.execute(update_query, params)
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Crawler not found")
        
        # Get updated crawler_setting only
        select_query = """
        SELECT id, crawler_id, alias, max_browser_count, create_time, update_time
        FROM crawler_setting
        WHERE id = %s
        """
        cursor.execute(select_query, (request.id,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Crawler status not found")
        
        db.commit()
        
        # Format datetime field
        result['last_heartbeat'] = format_datetime(result['last_heartbeat'])
        
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cursor:
            cursor.close()

@app.post("/crawler/delete")
def delete_crawlers(req: DeleteRequest, db=Depends(get_db_connection)):
    exists_ids = None
    if req.ids!=None and len(req.ids)>0:
        cursor = None
        try:
            db.start_transaction()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id FROM crawler_info WHERE id IN (%s)" % ','.join(['%s']*len(req.ids)), req.ids)
            exists_ids = [row['id'] for row in cursor.fetchall()]
            cursor.execute("DELETE FROM crawler_info WHERE id IN (%s)" % ','.join(['%s']*len(exists_ids)), exists_ids)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor:
                cursor.close()
    return {"ids": exists_ids}

@app.post("/session/grid", response_model=PageResponse)
def session_grid(request: SessionGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # Base query
        query = """
        SELECT cs.id, cs.uuid, cs.init_time, cs.url, cs.destroy_time, cs.create_time, cs.update_time,
               ci.uuid as crawler_uuid, ci.host_name, ci.internal_ip, ci.external_ip,
               cset.alias
        FROM crawler_session cs
        LEFT JOIN crawler_info ci ON cs.crawler_id = ci.id
        LEFT JOIN crawler_setting cset ON cs.crawler_id = cset.id
        """
        
        # Count query
        count_query = """
        SELECT COUNT(*) as total
        FROM crawler_session cs
        LEFT JOIN crawler_info ci ON cs.crawler_id = ci.id
        LEFT JOIN crawler_setting cset ON cs.crawler_id = cset.id
        """
        
        # Build WHERE clause for session grid
        conditions = []
        params = []
        if request.crawler_id:
            conditions.append("cs.crawler_id = %s")
            params.append(request.crawler_id)
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(cs.uuid LIKE %s OR ci.uuid LIKE %s OR ci.host_name LIKE %s OR ci.internal_ip LIKE %s OR ci.external_ip LIKE %s OR cset.alias LIKE %s)")
            params.extend([like_value, like_value, like_value, like_value, like_value, like_value])
        
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

@app.post("/session/delete")
def delete_sessions(req: DeleteRequest, db=Depends(get_db_connection)):
    exists_ids = None
    if req.ids!=None and len(req.ids)>0:
        cursor = None
        try:
            db.start_transaction()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id FROM crawler_session WHERE id IN (%s)" % ','.join(['%s']*len(req.ids)), req.ids)
            exists_ids = [row['id'] for row in cursor.fetchall()]
            cursor.execute("DELETE FROM crawler_session WHERE id IN (%s)" % ','.join(['%s']*len(exists_ids)), exists_ids)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor:
                cursor.close()
    return {"ids": exists_ids}

@app.post("/log/grid", response_model=PageResponse)
def log_grid(request: LogGridRequest, db=Depends(get_db_connection)):
    cursor = None
    try:
        cursor = db.cursor(dictionary=True)
        
        # Base query
        query = """
        SELECT cl.id, cl.url, cl.request_time, cl.response_time, cl.status_code, cl.create_time, cl.update_time,
               cs.uuid, ci.uuid as crawler_uuid, ci.host_name, ci.external_ip, ci.internal_ip, cset.alias
        FROM crawler_log cl
        LEFT JOIN crawler_session cs ON cl.crawler_session_id = cs.id
        LEFT JOIN crawler_info ci ON cs.crawler_id = ci.id
        LEFT JOIN crawler_setting cset ON cs.crawler_id = cset.id
        """
        
        # Count query
        count_query = """
        SELECT COUNT(*) as total
        FROM crawler_log cl
        LEFT JOIN crawler_session cs ON cl.crawler_session_id = cs.id
        LEFT JOIN crawler_info ci ON cs.crawler_id = ci.id
        LEFT JOIN crawler_setting cset ON cs.crawler_id = cset.id
        """
        
        # Build WHERE clause for log grid
        conditions = []
        params = []
        if request.session_id:
            conditions.append("cl.crawler_session_id = %s")
            params.append(request.session_id)
        if request.keyword:
            like_value = f"%{request.keyword}%"
            conditions.append("(cl.url LIKE %s OR cs.uuid LIKE %s OR ci.uuid LIKE %s OR ci.host_name LIKE %s OR ci.external_ip LIKE %s OR ci.internal_ip LIKE %s OR cset.alias LIKE %s)")
            params.extend([like_value, like_value, like_value, like_value, like_value, like_value, like_value])
        
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

@app.post("/log/delete")
def delete_logs(req: DeleteRequest, db=Depends(get_db_connection)):
    exists_ids = None
    if req.ids is not None and len(req.ids) > 0:
        cursor = None
        try:
            db.start_transaction()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id FROM crawler_log WHERE id IN (%s)" % ','.join(['%s']*len(req.ids)), req.ids)
            exists_ids = [row['id'] for row in cursor.fetchall()]
            cursor.execute("DELETE FROM crawler_log WHERE id IN (%s)" % ','.join(['%s']*len(exists_ids)), exists_ids)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if cursor:
                cursor.close()
    return {"ids": exists_ids}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)