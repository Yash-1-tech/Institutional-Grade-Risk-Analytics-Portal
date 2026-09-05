-- Track individual bond characteristics
CREATE TABLE bonds (
    isin VARCHAR(12) PRIMARY KEY,
    issuer_name VARCHAR(100) NOT NULL,
    maturity_date DATE NOT NULL,
    coupon_rate NUMERIC(5, 4) NOT NULL, -- e.g., 0.0450 for 4.5%
    face_value NUMERIC(15, 2) DEFAULT 1000.00,
    payment_frequency INT DEFAULT 2 -- 1=Annual, 2=Semi-Annual
);

-- Track the term structure of interest rates over time
CREATE TABLE yield_curves (
    curve_date DATE NOT NULL,
    tenor_months INT NOT NULL, -- 3, 6, 12, 60, 120, 360
    rate NUMERIC(5, 4) NOT NULL,
    PRIMARY KEY (curve_date, tenor_months)
);

-- Map bonds to a user's portfolio
CREATE TABLE portfolio_positions (
    id BIGSERIAL PRIMARY KEY,
    portfolio_id UUID NOT NULL,
    bond_isin VARCHAR(12) REFERENCES bonds(isin),
    quantity INT NOT NULL,
    purchase_yield NUMERIC(5, 4)
);
