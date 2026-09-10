import pygame
import math
import random

HEIGHT= 800
WIDTH= 1200

FPS= 60

LANE_WIDTH= 100
ROAD_WIDTH= LANE_WIDTH * 3

CENTER_X= WIDTH // 2
CENTER_Y= HEIGHT // 2

INTERSECTION_HALF = ROAD_WIDTH // 2

BLACK= (0,0,0)
WHITE= (255,255,255)
RED= (250,10,10)
GREEN= (10,250,10)
YELLOW= (255,255,0)
ROAD_LINE= (211,211,211)
BACKGROUND_COLOR= (169,169,169)
LANE_LINE_COLOR= (192,192,192)
STOP_LINE_COLOR= (255,0,127)

CAR_LENGTH= 40
CAR_WIDTH= 20
CAR_SPEED= 120.0
CAR_ACCELERATION= 180.0
CAR_DECELERATION= 250.0
MIN_CAR_GAP= 50
CAR_COLORS = [
    (50, 120, 220),
    (220, 80, 70),
    (230, 170, 50),
    (120, 80, 200),
    (50, 180, 170),
    (220, 120, 50),
]

SPAWN_INTERVAL= 1.7

NS_LEFT_TIME = 10.0
NS_THROUGH_TIME = 10.0
EW_LEFT_TIME = 10.0
EW_THROUGH_TIME = 10.0
YELLOW_TIME = 3.0
STOP_DISTANCE = 35

NORTH= "north"
SOUTH= "south"
EAST= "east"
WEST= "west"

RIGHT = "right"
LEFT = "left"
THROUGH = "through"

APPROACHING= "approaching"
WAITING= "waiting"
CROSSING= "crossing"
TURNING= "turning"
LEAVING= "leaving"


def clamp(value,maximum, minimun):
    return max(min(maximum,value),minimun)

def distance(X1,X2,Y1,Y2):
    return math.sqrt(((X1-X2)**2 ) + ((Y1-Y2)**2))

class Phase :
    def __init__(self,name,duration,allowed_movements):
        self.name= name
        self.duration= duration
        self.allowed_movements= allowed_movements

    def allows(self, approach,movement) :
        return (approach, movement) in self.allowed_movements

class traffic_controller:
    def __init__(self):
        self.Phases=[
            Phase(
                "NS_THROUGH",
                NS_THROUGH_TIME,
                [
                (NORTH,THROUGH),
                (SOUTH,THROUGH),
                (NORTH,RIGHT),
                (SOUTH,RIGHT),
                ]
            ),
            Phase(
                "NS_LEFT",
                NS_LEFT_TIME,
                [
                (NORTH,LEFT),
                (SOUTH,LEFT)
                ]
            ),
            Phase(
                "EW_THROUGH",
                EW_THROUGH_TIME,
                [
                    (WEST,THROUGH),
                    (EAST,THROUGH),
                    (WEST,RIGHT),
                    (EAST,RIGHT),
                ]
            ),
            Phase(
                "EW_LEFT",
                EW_LEFT_TIME,
                [
                    (WEST,LEFT),
                    (EAST,LEFT)
                ]
            )       
        ]
        self.current_phase_index=0
        self.phase_timer=0.0
        self.yellow= False
        self.yellow_timer=0.0

    @property
    def current_phase(self):
        return self.Phases[self.current_phase_index]

    def update(self,dt):
        if  self.yellow:
            self.yellow_timer += dt
            if self.yellow_timer >= YELLOW_TIME:
                self.yellow= False
                self.yellow_timer= 0.0
                self.current_phase_index= (self.current_phase_index + 1) % len(self.Phases)
                self.phase_timer=0.0
            return
        self.phase_timer+= dt
        if self.phase_timer >= self.current_phase.duration:
            self.yellow= True
            self.yellow_timer= 0.0

    def get_light_state(self, approach, movement):
        current_phase = self.Phases[self.current_phase_index]

        if (approach, movement) in current_phase.allowed_movements:
            if self.yellow:
                return "YELLOW"
            return "GREEN"
        return "RED"        
    def is_movement_allowed(self,approach,movement):
        if self.yellow:
            return False
        return self.current_phase.allows(approach,movement)

    def get_signal(self,approach,movement):
        if self.yellow:
            if self.current_phase.allows(approach,movement):
                return YELLOW
            return RED
        if self.current_phase.allows(approach,movement):
            return GREEN
        return RED
    def get_remaining_time(self):
        if self.yellow:
            return max(0,YELLOW_TIME - self.yellow_timer)
        return max(0,self.current_phase.duration - self.phase_timer)

class traffic_light:
    def __init__(self,x,y,approach,controller):
        self.x=x
        self.y=y
        self.approach=approach
        self.controller=controller

    def draw(self, screen):
    
            left_signal = self.controller.get_signal(
                self.approach,
                LEFT
            )
    
            through_signal = self.controller.get_signal(
                self.approach,
                THROUGH
            )
            housing = pygame.Rect(
                self.x - 20,
                self.y - 45,
                40,
                90,
            )
    
            pygame.draw.rect(
                screen,
                BLACK,
                housing,
                border_radius=8,
            )
            self.draw_light(
                screen,
                self.x,
                self.y - 20,
                left_signal,
            )
            self.draw_light(
                screen,
                self.x,
                self.y + 20,
                through_signal,
            )
    
    def draw_light(self, screen, x, y, signal):
    
        pygame.draw.circle(
            screen,
            signal,
            (int(x), int(y)),
            10,
        )
def get_bezier_point(p0, p1, p2, t):
    """Calculates (x, y) along a quadratic Bezier curve for t in [0.0, 1.0]."""
    u = 1 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
    return x, y
class Car:
    def __init__(self, approach, movement):
        self.turn_progress = 0.0
        self.p0 = None
        self.p1 = None
        self.p2 = None
        self.approach = approach
        self.movement = movement
        self.speed = CAR_SPEED
        self.target_speed = CAR_SPEED
        
        self.waiting_time = 0.0
        self.total_time = 0.0
        self.state = APPROACHING
        self.color = random.choice(CAR_COLORS)
        
        self.has_entered_intersection = False
        self.finished = False
        
        self.direction_x = 0
        self.direction_y = 1
        self.x = 0.0
        self.y = 0.0
        self.initialize_position()

    def initialize_position(self):
        offset = LANE_WIDTH * 0.7  

        if self.approach == NORTH:
            if self.movement == LEFT:
                self.x = CENTER_X - offset + 25 
            else:
                self.x = CENTER_X - offset - 50 + 25 if self.movement != RIGHT else CENTER_X - (ROAD_WIDTH // 2) + 5
            self.y = -CAR_LENGTH
            self.direction_x, self.direction_y = 0, 1

        elif self.approach == SOUTH:
            if self.movement == LEFT:
                self.x = CENTER_X + offset - 25
            else:
                self.x = CENTER_X + offset - 25 + 50 if self.movement != RIGHT else CENTER_X + (ROAD_WIDTH // 2) - 5
            self.y = HEIGHT + CAR_LENGTH
            self.direction_x, self.direction_y = 0, -1

        elif self.approach == EAST:
            self.x = WIDTH + CAR_LENGTH
            if self.movement == LEFT:
                self.y = CENTER_Y - offset + 25
            else:
                self.y = CENTER_Y - offset + 25 - 50 if self.movement != RIGHT else CENTER_Y - (ROAD_WIDTH // 2) + 5
            self.direction_x, self.direction_y = -1, 0

        elif self.approach == WEST:
            self.x = -CAR_LENGTH
            if self.movement == LEFT:
                self.y = CENTER_Y + offset - 25
            else:
                self.y = CENTER_Y + offset - 25 + 50 if self.movement != RIGHT else CENTER_Y + (ROAD_WIDTH // 2) - 5
            self.direction_x, self.direction_y = 1, 0

    def stop_line_position(self):
        if self.approach == NORTH:
            return CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE
        if self.approach == SOUTH:
            return CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE
        if self.approach == EAST:
            return CENTER_X + INTERSECTION_HALF + STOP_DISTANCE
        if self.approach == WEST:
            return CENTER_X - INTERSECTION_HALF - STOP_DISTANCE

    def distance_to_stop_line(self):
        if self.approach == NORTH:
            return self.stop_line_position() - self.y
        if self.approach == SOUTH:
            return self.y - self.stop_line_position()
        if self.approach == EAST:
            return self.x - self.stop_line_position()
        if self.approach == WEST:
            return self.stop_line_position() - self.x

    def inside_intersection(self):
        return (
            CENTER_X - INTERSECTION_HALF <= self.x <= CENTER_X + INTERSECTION_HALF and
            CENTER_Y - INTERSECTION_HALF <= self.y <= CENTER_Y + INTERSECTION_HALF
        )

    def has_passed_stop_line(self):      
        stop_pos = self.stop_line_position()
        if self.approach == NORTH:
            return self.y >= stop_pos
        elif self.approach == SOUTH:
            return self.y <= stop_pos
        elif self.approach == EAST:
            return self.x <= stop_pos
        elif self.approach == WEST:
            return self.x >= stop_pos
        return False

    def should_stop(self, controller, cars):
        # inside intersection
        if self.state in (TURNING, LEAVING) or self.has_entered_intersection or self.has_passed_stop_line():
            return False

        # light state before entering intersection
        light_state = controller.get_light_state(self.approach, self.movement)
        dist = self.distance_to_stop_line()

        if dist > 0:
            if light_state == "RED":
                if dist <= 60:
                    return True
            elif light_state == "YELLOW":
                safe_stopping_distance = (self.speed ** 2) / (2 * CAR_DECELERATION) + 15
                if dist > safe_stopping_distance:
                    return True

        # 3. Check for queuing behind other cars in approach lane
        return self.check_car_in_front(cars)

    def check_car_in_front(self, cars):
        for other in cars:
            if other is self:
                continue
            
            if other.approach != self.approach or other.movement != self.movement:
                continue

            if other.has_entered_intersection or other.state in (TURNING, LEAVING):
                continue

            if self.approach == NORTH and other.y > self.y:
                if (other.y - self.y) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == SOUTH and other.y < self.y:
                if (self.y - other.y) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == EAST and other.x < self.x:
                if (self.x - other.x) < CAR_LENGTH + MIN_CAR_GAP:
                    return True
            elif self.approach == WEST and other.x > self.x:
                if (other.x - self.x) < CAR_LENGTH + MIN_CAR_GAP:
                    return True

        return False

    def update(self, dt, controller, cars):
        self.total_time += dt

        stopping = self.should_stop(controller, cars)

        if stopping:
            self.speed = max(0.0, self.speed - CAR_DECELERATION * dt)
            if self.speed == 0.0 and self.state != TURNING:
                self.state = WAITING
                self.waiting_time += dt
        else:
            if self.state == WAITING:
                self.state = APPROACHING
            self.speed = min(CAR_SPEED, self.speed + CAR_ACCELERATION * dt)

        # Handle turns vs linear movement
        if self.movement == LEFT and self.state != LEAVING:
            self.handle_left_turn(dt)
        elif self.movement == RIGHT and self.state != LEAVING:
            self.handle_right_turn(dt)

        # Linear position updates for APPROACHING, WAITING, and LEAVING states
        if self.state != TURNING:
            self.x += self.direction_x * self.speed * dt
            self.y += self.direction_y * self.speed * dt

        self.check_if_finished()

    def handle_left_turn(self, dt):
        if not self.has_entered_intersection and self.inside_intersection():
            self.has_entered_intersection = True
            self.state = TURNING
            self.setup_bezier_points()

        if self.state == TURNING:
            arc_length = 235.0
            self.turn_progress += (self.speed * dt) / arc_length

            if self.turn_progress >= 1.0:
                self.turn_progress = 1.0
                self.x, self.y = self.p2
                self.update_exit_direction()
                self.state = LEAVING  # Unlocks linear movement in update()
            else:
                prev_x, prev_y = self.x, self.y
                self.x, self.y = get_bezier_point(self.p0, self.p1, self.p2, self.turn_progress)
                
                dx, dy = self.x - prev_x, self.y - prev_y
                if dx != 0 or dy != 0:
                    mag = math.hypot(dx, dy)
                    self.direction_x, self.direction_y = dx / mag, dy / mag

    def setup_bezier_points(self):
        offset = LANE_WIDTH * 0.5

        if self.approach == NORTH:
            self.p0 = (CENTER_X - offset, CENTER_Y - INTERSECTION_HALF)
            self.p1 = (CENTER_X - offset, CENTER_Y + offset)
            self.p2 = (CENTER_X + INTERSECTION_HALF, CENTER_Y + offset)

        elif self.approach == SOUTH:
            self.p0 = (CENTER_X + offset, CENTER_Y + INTERSECTION_HALF)
            self.p1 = (CENTER_X + offset, CENTER_Y - offset)
            self.p2 = (CENTER_X - INTERSECTION_HALF, CENTER_Y - offset)

        elif self.approach == EAST:
            self.p0 = (CENTER_X + INTERSECTION_HALF, CENTER_Y - offset)
            self.p1 = (CENTER_X - offset, CENTER_Y - offset)
            self.p2 = (CENTER_X - offset, CENTER_Y + INTERSECTION_HALF)

        elif self.approach == WEST:
            self.p0 = (CENTER_X - INTERSECTION_HALF, CENTER_Y + offset)
            self.p1 = (CENTER_X + offset, CENTER_Y + offset)
            self.p2 = (CENTER_X + offset, CENTER_Y - INTERSECTION_HALF)

    def update_exit_direction(self):
        if self.approach == NORTH:    # Exiting East bound
            self.direction_x, self.direction_y = 1, 0
        elif self.approach == SOUTH:  # Exiting West bound
            self.direction_x, self.direction_y = -1, 0
        elif self.approach == EAST:   # Exiting South bound
            self.direction_x, self.direction_y = 0, 1
        elif self.approach == WEST:   # Exiting North bound
            self.direction_x, self.direction_y = 0, -1

    def handle_right_turn(self, dt):
        if not self.has_entered_intersection and self.has_passed_stop_line():
            self.has_entered_intersection = True
            self.state = TURNING
            self.setup_right_turn_points()

        if self.state == TURNING:
            arc_length = 117.0
            self.turn_progress += (self.speed * dt) / arc_length

            if self.turn_progress >= 1.0:
                self.turn_progress = 1.0
                self.x, self.y = self.p2
                self.update_right_exit_direction()
                self.state = LEAVING  # Unlocks linear movement in update()
            else:
                prev_x, prev_y = self.x, self.y
                self.x, self.y = get_bezier_point(self.p0, self.p1, self.p2, self.turn_progress)
                
                dx, dy = self.x - prev_x, self.y - prev_y
                if dx != 0 or dy != 0:
                    mag = math.hypot(dx, dy)
                    self.direction_x, self.direction_y = dx / mag, dy / mag

    def setup_right_turn_points(self):

        if self.approach == NORTH:
            # North -> West
            self.p0 = (CENTER_X - (ROAD_WIDTH // 2) + 5, CENTER_Y - INTERSECTION_HALF)
            self.p1 = (CENTER_X - (ROAD_WIDTH // 2) + 5, CENTER_Y - (ROAD_WIDTH // 2) + 5)
            self.p2 = (CENTER_X - INTERSECTION_HALF, CENTER_Y - (ROAD_WIDTH // 2) + 5)

        elif self.approach == SOUTH:
            # South -> East
            self.p0 = (CENTER_X + (ROAD_WIDTH // 2) - 5, CENTER_Y + INTERSECTION_HALF)
            self.p1 = (CENTER_X + (ROAD_WIDTH // 2) - 5, CENTER_Y + (ROAD_WIDTH // 2) - 5)
            self.p2 = (CENTER_X + INTERSECTION_HALF, CENTER_Y + (ROAD_WIDTH // 2) - 5)

        elif self.approach == EAST:
            # East -> North
            self.p0 = (CENTER_X + INTERSECTION_HALF,  CENTER_Y - (ROAD_WIDTH // 2) + 5)
            self.p1 = (CENTER_X + (ROAD_WIDTH // 2) - 5,  CENTER_Y - (ROAD_WIDTH // 2) + 5)
            self.p2 = (CENTER_X + (ROAD_WIDTH // 2) - 5, CENTER_Y - INTERSECTION_HALF)

        elif self.approach == WEST:
            # West -> South
            self.p0 = (CENTER_X - INTERSECTION_HALF, CENTER_Y + (ROAD_WIDTH // 2) - 5)
            self.p1 = (CENTER_X - (ROAD_WIDTH // 2) + 5, CENTER_Y + (ROAD_WIDTH // 2) - 5)
            self.p2 = (CENTER_X - (ROAD_WIDTH // 2) + 5, CENTER_Y + INTERSECTION_HALF)
    def update_right_exit_direction(self):
        if self.approach == NORTH:    
            self.direction_x, self.direction_y = -1, 0
        elif self.approach == SOUTH:  
            self.direction_x, self.direction_y = 1, 0
        elif self.approach == EAST:   
            self.direction_x, self.direction_y = 0, -1
        elif self.approach == WEST:  
            self.direction_x, self.direction_y = 0, 1

    def check_if_finished(self):
        margin = 100
        if (
            self.x < -margin
            or self.x > WIDTH + margin
            or self.y < -margin
            or self.y > HEIGHT + margin
        ):
            self.finished = True
            self.state = LEAVING

    def draw(self, screen):
        angle = math.degrees(math.atan2(-self.direction_y, self.direction_x))

        surface = pygame.Surface((CAR_LENGTH, CAR_WIDTH), pygame.SRCALPHA)
        pygame.draw.rect(surface, self.color, (0, 0, CAR_LENGTH, CAR_WIDTH), border_radius=4)
        
        pygame.draw.rect(
            surface,
            (180, 220, 230),
            (CAR_LENGTH * 0.6, CAR_WIDTH * 0.15, CAR_LENGTH * 0.25, CAR_WIDTH * 0.7),
            border_radius=2
        )

        rotated_surface = pygame.transform.rotate(surface, angle)
        new_rect = rotated_surface.get_rect(center=(int(self.x), int(self.y)))
        screen.blit(rotated_surface, new_rect.topleft)
class Statistics:
    def __init__(self):
        self.total_cars= 0
        self.completed_cars=0
        self.total_waiting_time=0.0
        self.maximum_queue=0
        self.current_waiting_cars=0
    def register_car(self):
        self.total_cars+= 1
        
    def register_completed_car(self, car):
        self.completed_cars += 1
        self.total_waiting_time += car.waiting_time
            
    def update(self,cars):
        waiting=0
        for car in cars:
            if car.state == WAITING:
                waiting +=1
        self.current_waiting_cars = waiting
        self.maximum_queue = max(waiting, self.maximum_queue)
    def average_waiting_time(self):
        if self.completed_cars == 0:
            return 0
        return self.total_waiting_time / self.completed_cars
def get_traffic_state(cars,controller):

    total_north,north_through_right_waiting,north_left_waiting,total_south,south_through_right_waiting,south_left_waiting,total_west,west_through_right_waiting,west_left_waiting,total_east,east_through_right_waiting,east_left_waiting=0,0,0,0,0,0,0,0,0,0,0,0
    for car in cars:
        if car.approach == NORTH:
            if car.movement== LEFT and car.state==WAITING:
                north_left_waiting+=1
            elif car.state== WAITING:
                north_through_right_waiting+=1
            total_north+=1
        elif car.approach==SOUTH:
            if car.movement== LEFT and car.state==WAITING:
                south_left_waiting += 1
            elif car.state==WAITING:
                south_through_right_waiting += 1
            total_south += 1
        elif car.approach==WEST:
            if car.movement== LEFT and car.state==WAITING:
                west_left_waiting += 1
            elif car.state==WAITING:
                west_through_right_waiting += 1
            total_west += 1
        elif car.approach==EAST:
            if car.movement== LEFT and car.state==WAITING:
                east_left_waiting += 1
            elif car.state==WAITING:
                east_through_right_waiting += 1
            total_east += 1     
    currentphase=controller.current_phase_index
    phasetime=controller.phase_timer
    traffic_information=[total_north,north_through_right_waiting,north_left_waiting,total_south,south_through_right_waiting,south_left_waiting,total_west,west_through_right_waiting,west_left_waiting,total_east,east_through_right_waiting,east_left_waiting,currentphase,phasetime]

    return traffic_information
def draw_roads(screen):

    # Horizontal road

    horizontal_rect = pygame.Rect(
        0,
        CENTER_Y - ROAD_WIDTH // 2 -20,
        WIDTH,
        ROAD_WIDTH + 40 ,
    )

    pygame.draw.rect(
        screen,
        ROAD_LINE,
        horizontal_rect,
    )

    # Vertical road

    vertical_rect = pygame.Rect(
        CENTER_X - ROAD_WIDTH // 2 - 20,
        0,
        ROAD_WIDTH + 40,
        HEIGHT,
    )

    pygame.draw.rect(
        screen,
        ROAD_LINE,
        vertical_rect,
    )

    # Horizontal lane divider

    pygame.draw.line(
        screen,
        BLACK,
        (0, CENTER_Y),
        (CENTER_X - INTERSECTION_HALF, CENTER_Y),
        40,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (0, CENTER_Y + 70),
        (CENTER_X - INTERSECTION_HALF - 35, CENTER_Y + 70),
        2,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (0, CENTER_Y + 120),
        (CENTER_X - INTERSECTION_HALF - 35, CENTER_Y + 120),
        2,
    )

    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X + INTERSECTION_HALF + 35, CENTER_Y - 70),
        (WIDTH, CENTER_Y - 70),
        2,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X + INTERSECTION_HALF + 35, CENTER_Y - 120),
        (WIDTH, CENTER_Y - 120),
        2,
    )
    pygame.draw.line(
        screen,
        BLACK,
        (CENTER_X + INTERSECTION_HALF, CENTER_Y),
        (WIDTH, CENTER_Y),
        40,
    )

    # Vertical lane divider

    pygame.draw.line(
        screen,
        BLACK,
        (CENTER_X, 0),
        (CENTER_X, CENTER_Y - INTERSECTION_HALF),
        40,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X - 70, 0),
        (CENTER_X - 70, CENTER_Y - INTERSECTION_HALF - 35),
        2,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X - 120, 0),
        (CENTER_X - 120, CENTER_Y - INTERSECTION_HALF - 35),
        2,
    )

    pygame.draw.line(
        screen,
        BLACK,
        (CENTER_X, CENTER_Y + INTERSECTION_HALF),
        (CENTER_X, HEIGHT),
        40,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X + 70, CENTER_Y + INTERSECTION_HALF + 35),
        (CENTER_X + 70, HEIGHT),
        2,
    )
    pygame.draw.line(
        screen,
        LANE_LINE_COLOR,
        (CENTER_X + 120, CENTER_Y + INTERSECTION_HALF + 35),
        (CENTER_X + 120, HEIGHT),
        2,
    )

    # Stop lines

    # North
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - ROAD_WIDTH // 2 - 20 ,
            CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE,
        ),
        (
            CENTER_X + ROAD_WIDTH // 2 + 20,
            CENTER_Y - INTERSECTION_HALF - STOP_DISTANCE,
        ),
        4,
    )

    # South
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - ROAD_WIDTH // 2 - 20,
            CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE,
        ),
        (
            CENTER_X + ROAD_WIDTH // 2 + 20,
            CENTER_Y + INTERSECTION_HALF + STOP_DISTANCE,
        ),
        4,
    )

    # East
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X + INTERSECTION_HALF + STOP_DISTANCE,
            CENTER_Y - ROAD_WIDTH // 2 - 20,
        ),
        (
            CENTER_X + INTERSECTION_HALF + STOP_DISTANCE,
            CENTER_Y + ROAD_WIDTH // 2 + 20,
        ),
        4,
    )

    # West
    pygame.draw.line(
        screen,
        STOP_LINE_COLOR,
        (
            CENTER_X - INTERSECTION_HALF - STOP_DISTANCE,
            CENTER_Y - ROAD_WIDTH // 2 - 20,
        ),
        (
            CENTER_X - INTERSECTION_HALF - STOP_DISTANCE,
            CENTER_Y + ROAD_WIDTH // 2 + 20,
        ),
        4,
    )
def create_traffic_lights(controller):

    lights = []

    lights.append(
        traffic_light(
            CENTER_X +1,
            CENTER_Y - 130,
            NORTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X + 1,
            CENTER_Y + 130,
            SOUTH,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X + 130,
            CENTER_Y ,
            EAST,
            controller,
        )
    )

    lights.append(
        traffic_light(
            CENTER_X - 130,
            CENTER_Y ,
            WEST,
            controller,
        )
    )

    return lights
def spawn_car(cars):

    approach = random.choice([
        NORTH,
        SOUTH,
        EAST,
        WEST,
    ])

    movement = random.choice([
        LEFT,
        THROUGH,
        RIGHT,
    ])

    new_car = Car(
        approach,
        movement,
    )

    # Avoid spawning directly on top of another car.
    for car in cars:

        if distance(
            new_car.x,
            new_car.y,
            car.x,
            car.y,
        ) < CAR_LENGTH * 2:

            return None

    cars.append(new_car)

    return new_car
def draw_information(
    screen,
    font,
    controller,
    statistics,
):

    lines = [

        f"Phase: {controller.current_phase.name}",

        f"Phase time remaining: "
        f"{controller.get_remaining_time():.1f}s",

        f"Cars generated: "
        f"{statistics.total_cars}",

        f"Cars completed: "
        f"{statistics.completed_cars}",

        f"Waiting cars: "
        f"{statistics.current_waiting_cars}",

        f"Maximum queue: "
        f"{statistics.maximum_queue}",

        f"Average waiting time: "
        f"{statistics.average_waiting_time():.2f}s",
    ]

    y = 15

    for text in lines:

        surface = font.render(
            text,
            True,
            WHITE,
        )

        screen.blit(
            surface,
            (15, y),
        )

        y += 25
def main():

    pygame.init()

    screen = pygame.display.set_mode(
        (WIDTH, HEIGHT)
    )

    pygame.display.set_caption(
        "AI Traffic Light Simulation - Version 1"
    )

    clock = pygame.time.Clock()

    font = pygame.font.SysFont(
        "Arial",
        18,
    )

    controller = traffic_controller()

    statistics = Statistics()

    traffic_lights = create_traffic_lights(
        controller
    )

    cars = []

    running = True
    print_time=0.0
    spawn_timer = 0.0



    while running:



        dt = clock.tick(FPS) / 1000.0


        dt = min(dt, 0.1)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                running = False


        controller.update(dt)



        spawn_timer += dt

        if spawn_timer >= SPAWN_INTERVAL:

            spawn_timer = 0

            new_car = spawn_car(cars)

            if new_car is not None:

                statistics.register_car()


        for car in cars:

            car.update(
                dt,
                controller,
                cars,
            )



        remaining_cars = []

        for car in cars:

            if car.finished:

                statistics.register_completed_car(
                    car
                )

            else:

                remaining_cars.append(car)

        cars = remaining_cars



        statistics.update(cars)

        print_time+=dt
        state_list=get_traffic_state(cars,controller)
        if print_time>=5.0:
            print_time=0.0
            print(state_list)


        screen.fill(
            BACKGROUND_COLOR
        )

        draw_roads(screen)


        for light in traffic_lights:

            light.draw(screen)


        for car in cars:

            car.draw(screen)


        draw_information(
            screen,
            font,
            controller,
            statistics,
        )


        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

        



         