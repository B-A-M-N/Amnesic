from dataclasses import dataclass

@dataclass
class Employee:
    name: str
    hourly_rate: float
    hours_worked: float


def calculate_net_pay(employee: Employee) -> float:
    gross_pay = employee.hours_worked * employee.hourly_rate
    net_pay = gross_pay - (gross_pay * 0.20)
    return net_pay