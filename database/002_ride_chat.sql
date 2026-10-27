CREATE TABLE IF NOT EXISTS ride_messages (
 id BIGINT PRIMARY KEY AUTO_INCREMENT,
 ride_id BIGINT NOT NULL,
 sender_id BIGINT NOT NULL,
 body VARCHAR(2000) NOT NULL,
 client_key CHAR(36) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY (ride_id) REFERENCES rides(id),
 FOREIGN KEY (sender_id) REFERENCES users(id),
 UNIQUE KEY message_retry (sender_id,client_key),
 INDEX ride_message_order (ride_id,id)
);
CREATE TABLE IF NOT EXISTS ride_chat_reads (
 ride_id BIGINT NOT NULL,
 user_id BIGINT NOT NULL,
 last_message_id BIGINT NOT NULL DEFAULT 0,
 PRIMARY KEY (ride_id,user_id),
 FOREIGN KEY (ride_id) REFERENCES rides(id),
 FOREIGN KEY (user_id) REFERENCES users(id)
);
