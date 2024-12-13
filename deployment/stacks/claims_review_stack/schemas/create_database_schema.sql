
CREATE TABLE INSURED_PERSON (
    insured_id SERIAL PRIMARY KEY,
    insured_name VARCHAR(100) NOT NULL,
    insured_group_number VARCHAR(100) NOT NULL,
    insured_plan_name VARCHAR(100) NOT NULL,
    insured_birth_date DATE NOT NULL,
    insured_policy_number VARCHAR(100) NOT NULL UNIQUE,
    phone_number VARCHAR(15),
    address TEXT
);

CREATE TABLE PATIENT (
    patient_id SERIAL PRIMARY KEY,
    insured_id INT NOT NULL,
    patient_firstname VARCHAR(100) NOT NULL,
    patient_lastname VARCHAR(100) NOT NULL,
    patient_birth_date DATE NOT NULL,
    relationship_to_insured VARCHAR(100) NOT NULL,
    phone_number VARCHAR(15),
    sex VARCHAR(5),
    address TEXT,    
    FOREIGN KEY (insured_id) REFERENCES INSURED_PERSON(insured_id)
);

CREATE TABLE CLAIM (
    claim_id SERIAL PRIMARY KEY,
    patient_id INT NOT NULL,
    claim_date DATE NOT NULL,
    diagnosis_1 VARCHAR(50),
    diagnosis_2 VARCHAR(50),
    diagnosis_3 VARCHAR(50),
    diagnosis_4 VARCHAR(50),
    balanceDue DECIMAL(10, 2),
    amountPaid DECIMAL(10, 2),
    total_charges DECIMAL(10, 2) NOT NULL,
    claim_status VARCHAR(50) NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES PATIENT(patient_id)
);

CREATE TABLE SERVICE (
    service_id SERIAL PRIMARY KEY,
    claim_id INT NOT NULL,
    date_of_service DATE,
    place_of_service VARCHAR(10),
    type_of_service VARCHAR(10),
    procedure_code INT,
    charge_amount DECIMAL(10, 2),
    FOREIGN KEY (claim_id) REFERENCES CLAIM(claim_id)
);
