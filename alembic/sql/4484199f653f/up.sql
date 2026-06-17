CREATE SCHEMA IF NOT EXISTS catalog;
--
-- Name: product_categories; Type: TABLE; Schema: catalog; Owner: app_user
--

CREATE TABLE catalog.product_categories (
    id serial PRIMARY KEY,
    name text NOT NULL
);

--
-- Name: products; Type: TABLE; Schema: catalog; Owner: app_user
--

CREATE TABLE catalog.products (
    id serial PRIMARY KEY,
    sku VARCHAR(30) UNIQUE NOT NULL,
    name text NOT NULL,
    price decimal NOT NULL,
    category_id integer NOT NULL,
    CONSTRAINT category_ref FOREIGN KEY (category_id) REFERENCES catalog.product_categories (id)
);

--
-- Name: warehouses; Type: TABLE; Schema: catalog; Owner: app_user
--

CREATE TABLE catalog.warehouses (
    id serial PRIMARY KEY,
    city text NOT NULL,
    address text NOT NULL,
    label text,
    is_central boolean NOT NULL
);