CREATE TABLE departments (
    department_id INTEGER PRIMARY KEY,
    department_name TEXT NOT NULL
);

CREATE TABLE employees (
    employee_id INTEGER PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    salary REAL NOT NULL,
    hire_date TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    amount REAL NOT NULL,
    order_date TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

INSERT INTO departments (department_id, department_name) VALUES
    (1, 'Engineering'),
    (2, 'Sales'),
    (3, 'Marketing');

INSERT INTO employees (employee_id, first_name, last_name, department_id, salary, hire_date) VALUES
    (1, 'Alice', 'Nguyen', 1, 95000, '2019-03-14'),
    (2, 'Bob', 'Smith', 2, 72000, '2020-07-01'),
    (3, 'Carla', 'Diaz', 1, 105000, '2018-11-23'),
    (4, 'David', 'Kim', 3, 68000, '2021-02-09'),
    (5, 'Eve', 'Johnson', 2, 81000, '2017-06-30');

INSERT INTO orders (order_id, employee_id, customer_name, amount, order_date) VALUES
    (1, 2, 'Acme Corp', 15000, '2023-01-15'),
    (2, 2, 'Globex Inc', 8200, '2023-02-20'),
    (3, 5, 'Initech', 23000, '2023-03-05'),
    (4, 5, 'Umbrella LLC', 4300, '2023-04-11');
