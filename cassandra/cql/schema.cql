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
    stars int, 
    PRIMARY KEY(review_id,business_id)
);

CREATE TABLE IF NOT EXISTS nosql.review_by_user(
    user_id TEXT,
    review_id TEXT,
    reviewed_at DATE,
    stars INT,
    PRIMARY KEY(user_id,review_id)
);

create table if NOT EXISTS nosql.tips_by_business(
    tipped_at date,
    business_id text ,
    tip_id int, 
    primary key(business_id, tip_id)
);

create table if NOT EXISTS nosql.checks_by_business(
    business_id text,
    checked_at date,
    primary key(business_id, checked_at)
);

create table if NOT EXISTS nosql.users_by_business(
  id text ,
  tip_business_id text,
  tipped_at date,
  primary key(id,tip_business_id)
);

create table if NOT EXISTS nosql.user_by_personality_score(
user_id text primary key,
friends int, 
elite int, 
cool int, 
fans int 
);

create table if NOT EXISTS nosql.user_by_friends(
    user_id text ,
    friend_id text,
    friend_name varchar, 
    primary key(user_id,friend_id )
);

create table if NOT EXISTS nosql.review(
    id text primary key, 
    stars int, 
    username varchar 
); 
