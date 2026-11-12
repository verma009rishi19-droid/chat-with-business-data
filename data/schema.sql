-- 02-schema.sql
-- Production schema for Quick-Commerce / Blinkit-style business data warehouse

DROP TABLE IF EXISTS customer_ratings CASCADE;
DROP TABLE IF EXISTS deliveries CASCADE;
DROP TABLE IF EXISTS inventory CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS dark_stores CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

CREATE TABLE categories (
    category_id VARCHAR(32) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id VARCHAR(32) PRIMARY KEY,
    category_id VARCHAR(32) NOT NULL REFERENCES categories(category_id),
    product_name VARCHAR(150) NOT NULL,
    sku VARCHAR(50) UNIQUE NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    cost_price NUMERIC(10, 2) NOT NULL CHECK (cost_price >= 0),
    is_perishable BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE dark_stores (
    store_id VARCHAR(32) PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    zone VARCHAR(50) NOT NULL,
    hourly_capacity INT NOT NULL DEFAULT 120
);

CREATE TABLE customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    city VARCHAR(50) NOT NULL,
    signup_date DATE NOT NULL,
    customer_tier VARCHAR(20) NOT NULL CHECK (customer_tier IN ('Standard', 'Silver', 'Gold', 'VIP'))
);

CREATE TABLE orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    store_id VARCHAR(32) NOT NULL REFERENCES dark_stores(store_id),
    order_status VARCHAR(20) NOT NULL CHECK (order_status IN ('Delivered', 'Cancelled', 'Returned')),
    order_timestamp TIMESTAMP NOT NULL,
    delivery_fee NUMERIC(6, 2) NOT NULL DEFAULT 15.00,
    total_amount NUMERIC(10, 2) NOT NULL CHECK (total_amount >= 0),
    payment_method VARCHAR(30) NOT NULL
);

CREATE TABLE order_items (
    item_id VARCHAR(32) PRIMARY KEY,
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id VARCHAR(32) NOT NULL REFERENCES products(product_id),
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0),
    total_price NUMERIC(10, 2) NOT NULL CHECK (total_price >= 0)
);

CREATE TABLE deliveries (
    delivery_id VARCHAR(32) PRIMARY KEY,
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    rider_id VARCHAR(32) NOT NULL,
    dispatch_time TIMESTAMP NOT NULL,
    delivery_time TIMESTAMP,
    delivery_duration_minutes NUMERIC(6, 2),
    delay_minutes NUMERIC(6, 2) NOT NULL DEFAULT 0,
    weather_condition VARCHAR(30) NOT NULL DEFAULT 'Clear',
    delivery_rating INT CHECK (delivery_rating BETWEEN 1 AND 5)
);

CREATE TABLE inventory (
    inventory_id VARCHAR(32) PRIMARY KEY,
    store_id VARCHAR(32) NOT NULL REFERENCES dark_stores(store_id),
    product_id VARCHAR(32) NOT NULL REFERENCES products(product_id),
    stock_on_hand INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 20,
    last_restocked_at TIMESTAMP,
    CONSTRAINT uq_store_product UNIQUE (store_id, product_id)
);

CREATE TABLE customer_ratings (
    rating_id VARCHAR(32) PRIMARY KEY,
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id VARCHAR(32) NOT NULL REFERENCES products(product_id),
    rating_score INT NOT NULL CHECK (rating_score BETWEEN 1 AND 5),
    feedback_tag VARCHAR(50),
    comment TEXT
);

-- Performance Indexes for Analytics Queries
CREATE INDEX idx_orders_timestamp ON orders(order_timestamp);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_store ON orders(store_id);
CREATE INDEX idx_orders_status ON orders(order_status);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

CREATE INDEX idx_deliveries_order ON deliveries(order_id);
CREATE INDEX idx_deliveries_weather ON deliveries(weather_condition);
CREATE INDEX idx_deliveries_delay ON deliveries(delay_minutes);

CREATE INDEX idx_inventory_store ON inventory(store_id);
CREATE INDEX idx_inventory_product ON inventory(product_id);

CREATE INDEX idx_ratings_product ON customer_ratings(product_id);
CREATE INDEX idx_ratings_order ON customer_ratings(order_id);

-- Explicitly grant SELECT to the read-only role if it exists
DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'readonly_analyst') THEN
      GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_analyst;
   END IF;
END
$do$;
