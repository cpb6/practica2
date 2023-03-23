
import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value

SOUTH = 1
NORTH = 0

NCARS = 50
NPED = 10
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.patata = Value('i', 0)
        self.turno = Value('i',0)
        #turno 0 para los coches de dirección norte
        # turno 1 para los coches de direccion sur
        #turno 2 para los peatones
        self.carsNorth = Value('i',0) #Coches en direccion norte dentro del puente
        self.carsSouth = Value('i',0) #coches en dirección sur dentro del puente
        self.pedestrian= Value('i',0) # peatones dentro del puente 
        self.carsNorth_waiting = Value('i',0) # coches en direccion norte esperando
        self.carsSouth_waiting = Value('i',0) # coches en dirección sur esperando
        self.Pedestrian_waiting = Value('i',0) #peatones esperando 
        self.no_NorthP = Condition(self.mutex) #No hay coches en dirección norte ni peatones
        self.no_SouthP = Condition(self.mutex) # No hay coches en dirección sur ni peatones
        self.no_Cars = Condition(self.mutex) # No hay coches
        
    def are_no_SouthPed(self):
        return (self.carsSouth.value == 0 and self.pedestrian.value ==0) and \
                ( self.turno.value==0 or ( self.carsSouth_waiting.value ==0 and self.Pedestrian_waiting.value ==0))

    def are_no_NorthPed(self):
        return (self.carsNorth.value == 0 and self.pedestrian.value ==0) and \
                ( self.turno.value==1 or ( self.carsNorth_waiting.value ==0 and self.Pedestrian_waiting.value ==0))


    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        if direction == 0:
            self.carsNorth_waiting.value += 1
            self.no_SouthP.wait_for(self.are_no_SouthPed)
            self.carsNorth_waiting.value -= 1
            self.carsNorth.value += 1
        else :
            self.carsSouth_waiting.value +=1
            self.no_NorthP.wait_for(self.are_no_NorthPed)
            self.carsSouth_waiting.value -=1
            self.carsSouth.value += 1
        self.mutex.release()

    def controlturno(self):
      if self.turno.value == 0 and self.carsNorth_waiting.value==0 and (self.carsSouth_waiting.value>0 and self.Pedestrian_waiting.value>0):
        self.turno.value = 1
      elif self.turno.value == 1 and self.carsSouth_waiting.value==0 and (self.carsNorth_waiting.value>0 and self.Pedestrian_waiting.value>0):
        self.turno.value = 2
      elif self.turno.value == 2 and self.Pedestrian_waiting.value==0 and (self.carsNorth_waiting.value>0 and self.carsSouth_waiting.value>0):
        self.turno.value= 0
    # Controlamos el turno para evitar que estén a la espera dos grupos de procesos 
    # distintos y en turno le pertenezca a otro que no requiere acceso

       
    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.patata.value += 1
        if direction==0 :
            self.carsNorth.value -= 1
            self.turno.value = 1
            if self.carsNorth.value==0:
                self.controlturno()
                self.no_NorthP.notify_all()
                self.no_Cars.notify_all()
        else: 
            self.carsSouth.value -= 1
            self.turno.value=2 
            if self.carsSouth.value==0:
                self.controlturno()
                self.no_Cars.notify_all()
                self.no_SouthP.notify_all()
        self.mutex.release()
        
    
    def are_no_cars(self):
        return (self.carsNorth.value==0 and self.carsSouth.value==0) and \
                ( self.turno.value==2 or (self.carsNorth_waiting.value==0 and self.carsSouth_waiting.value==0))
        
        

    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        self.Pedestrian_waiting.value += 1
        self.no_Cars.wait_for(self.are_no_cars)
        self.Pedestrian_waiting.value -= 1
        self.pedestrian.value += 1
        self.mutex.release()

    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        self.pedestrian.value -= 1
        self.turno.value = 0
        if self.pedestrian.value==0:
            self.controlturno()
            self.no_NorthP.notify_all()
            self.no_SouthP.notify_all()
        self.mutex.release()

    def __repr__(self) -> str:
        return f'Monitor: {self.patata.value}'

def delay_car_north() -> None:
  lower_limit = TIME_IN_BRIDGE_CARS[0] - TIME_IN_BRIDGE_CARS[1]
  upper_limit = TIME_IN_BRIDGE_CARS[0] + TIME_IN_BRIDGE_CARS[1]
  wait_time = random.uniform(lower_limit, upper_limit)
  time.sleep(wait_time)

def delay_car_south() -> None:
  lower_limit = TIME_IN_BRIDGE_CARS[0] - TIME_IN_BRIDGE_CARS[1]
  upper_limit = TIME_IN_BRIDGE_CARS[0] + TIME_IN_BRIDGE_CARS[1]
  wait_time = random.uniform(lower_limit, upper_limit)
  time.sleep(wait_time)

def delay_pedestrian() -> None:
  lower_limit = TIME_IN_BRIDGE_PEDESTRIAN[0] - TIME_IN_BRIDGE_PEDESTRIAN[1]
  upper_limit = TIME_IN_BRIDGE_PEDESTRIAN[0] + TIME_IN_BRIDGE_PEDESTRIAN[1]
  wait_time = random.uniform(lower_limit, upper_limit)
  time.sleep(wait_time)

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars_north = Process(target=gen_cars, args=(NORTH, TIME_CARS_NORTH, monitor))
    gcars_south = Process(target=gen_cars, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()
    print("END")


if __name__ == '__main__':
    main()