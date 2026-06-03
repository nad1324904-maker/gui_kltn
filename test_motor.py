class Car:
    def __init__(self, make, model):
        self.make = make
        self.model = model

    def start_engine(self):
        return f"The {self.make} {self.model}'s engine has started."
car = Car("Toyota", "Corolla")
str = car.start_engine()
print(str)