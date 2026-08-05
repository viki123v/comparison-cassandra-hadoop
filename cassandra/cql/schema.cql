CREATE TABLE IF NOT EXISTS nosql.user (
    username VARCHAR,
    id TEXT PRIMARY KEY,
    compliment_hot INT,
    compliment_cut INT,
    compliment_cool INT ,
    compliment_funny INT 
); 

CREATE TABLE IF NOT EXISTS nosql.business ( 
    longitude decimal,
    latitude decimal,
    id text PRIMARY KEY,
    review_count int 
);

CREATE TABLE IF NOT EXISTS nosql.review_by_business(
    review_id TEXT,
    business_id TEXT,
    stars INT,
    PRIMARY KEY (business_id, stars, review_id)
) WITH CLUSTERING ORDER BY (stars DESC, review_id ASC);

CREATE TABLE IF NOT EXISTS nosql.review_by_user(
    user_id TEXT,
    review_id TEXT,
    reviewed_at DATE,
    stars INT,
    PRIMARY KEY (user_id, stars, reviewed_at, review_id)
) WITH CLUSTERING ORDER BY (
    stars DESC,
    reviewed_at DESC,
    review_id ASC
);

CREATE TABLE IF NOT EXISTS nosql.tips_by_business(
    tipped_at DATE,
    business_id TEXT,
    tip_id INT,
    user_id TEXT,
    tip_text TEXT,
    PRIMARY KEY (business_id, tipped_at, tip_id)
) WITH CLUSTERING ORDER BY (tipped_at DESC, tip_id ASC);

create table if NOT EXISTS nosql.checks_by_business(
    business_id text,
    checked_at date,
    primary key(business_id, checked_at)
);

CREATE TABLE IF NOT EXISTS nosql.users_by_business(
    id TEXT,
    tip_business_id TEXT,
    tipped_at DATE,
    tip_id INT,
    PRIMARY KEY (tip_business_id, tipped_at, id, tip_id)
) WITH CLUSTERING ORDER BY (tipped_at DESC, id ASC, tip_id ASC);

CREATE TABLE IF NOT EXISTS nosql.user_by_personality_score(
    user_id TEXT PRIMARY KEY,
    friends INT,
    elite INT,
    cool INT,
    fans INT,
    personality_score DOUBLE,
    global_rank INT
);

create table if NOT EXISTS nosql.user_by_friends(
    user_id text ,
    friend_id text,
    friend_name varchar, 
    primary key(user_id,friend_id )
);

CREATE TABLE IF NOT EXISTS nosql.review(
    id TEXT PRIMARY KEY,
    stars INT,
    description TEXT,
    username VARCHAR
); 
