use jw103_db; 

drop table if exists comment;
drop table if exists registration;
drop table if exists eventcreated; 
drop table if exists person_interest;
drop table if exists org_account;
drop table if exists personal_account;
drop table if exists account;

-- Cascade or set null
-- event time-date, start time and end time

CREATE TABLE account (
  userid int PRIMARY KEY AUTO_INCREMENT,
  usertype enum('personal', 'org') not null,
  username varchar(40) not null,
  email varchar(40), 
  index (userid),
  
  hashedp char(60),
  unique(username),
  index(username)

)
ENGINE = InnoDB;

CREATE TABLE personal_account (
  userid int PRIMARY KEY,
  -- studentid char(9),
  foreign key (userid) references account(userid) 
    on delete cascade
    on update cascade
)
ENGINE = InnoDB;

CREATE TABLE org_account (
  userid int PRIMARY KEY,
  eboard varchar(500),
  orginfo varchar(2000), 
  foreign key (userid) references account(userid) 
    on delete cascade
    on update cascade
)
ENGINE = InnoDB;

CREATE TABLE person_interest (
  follower int,
  followed int, 
  foreign key (follower) references account(userid) 
    on delete cascade
    on update cascade
)
ENGINE = InnoDB;

CREATE TABLE eventcreated (
  eventid int PRIMARY KEY AUTO_INCREMENT,
  organizerid int,
  eventname varchar(50),
  eventtype enum('personal', 'org'), 
  shortdesc varchar(300), 
  eventdate date,
  starttime time,
  endtime time,
  eventloc varchar(50),
  rsvp enum('yes', 'no'), 
  eventtag varchar(300),
  fulldesc varchar(4000), 
  contactemail varchar(2000),
  spam varchar(100),
  index(eventid), 
  foreign key (organizerid) references account(userid) 
    on delete cascade
    on update cascade

)
ENGINE = InnoDB;

CREATE TABLE registration (
  eventid int,
  participant int,
  foreign key (eventid) references eventcreated(eventid) 
    on delete cascade
    on update cascade,
  foreign key (participant) references account(userid) 
    on delete cascade
    on update cascade
)
ENGINE = InnoDB;

CREATE TABLE comment (
  commentid int PRIMARY KEY,
  eventid int,
  senderid int,
  recieverID int,
  commentcontent varchar(1000),
  dateCreated timestamp,
  foreign key (eventid) references eventcreated(eventid) 
    on delete cascade
    on update cascade,
  foreign key (senderid) references account(userid) 
    on delete cascade
    on update cascade,
  foreign key (recieverid) references account(userid) 
    on delete cascade
    on update cascade
)
ENGINE = InnoDB;
