'''# MODERN PAYROLL SYSTEM
from dataclasses import dataclass
from typing import List

@dataclass
class Employee:
    name: str
    hourly_rate: float
    hours_worked: float

class PayrollSystem:
    def __init__(self):
        self.employees: List[Employee] = []
        self.global_tax_rate = 0.20

    def add_employee(self, employee: Employee):
        self.employees.append(employee)

    def calculate_pay(self, employee: Employee) -> float:
        gross = employee.hours_worked * employee.hourly_rate
        net = gross - (gross * self.global_tax_rate)
        return net

    def process_all_payrolls(self) -> List[float]:
        return [self.calculate_pay(emp) for emp in self.employees]

# Example usage:
# payroll = PayrollSystem()
# payroll.add_employee(Employee("John Doe", 25.0, 40.0))
# print(payroll.process_all_payrolls())'''