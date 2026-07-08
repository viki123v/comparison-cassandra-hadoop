# HBase — Column-Family NoSQL (Yelp Dataset)

## Current State
- HBase running via Docker (`dajobe/hbase` image)
- 5 tables created: `business`, `review`, `user`, `checkin`, `tip`
- Yelp dataset loaded in `yelp_data/` (not tracked in git)
- Test import validated: 5 rows per table, queries returning correct data

## Stack
- HBase (pseudo-distributed via Docker)
- Python + happybase (Thrift on port 9090)
- Yelp Academic Dataset (~9GB, 5 JSON files)

## Setup

```bash
# Start HBase
docker-compose up -d

# Install dependencies
pip install happybase

# Create tables
python3 create_tables.py
```

## Files
| File | Purpose |
|---|---|
| `docker-compose.yml` | HBase container config |
| `create_tables.py` | Creates all 5 HBase tables with column families |
| `yelp_data/` | Yelp dataset (not in git — add files manually) |

## Table Schema
| Table | Row Key | Column Families |
|---|---|---|
| business | business_id | info, location, meta |
| review | business_id#review_id | info, content |
| user | user_id | info, stats |
| checkin | business_id | data |
| tip | business_id#index | info |
