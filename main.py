import tkinter as tk
import random
import math

class BouncingBall:
    def __init__(self, canvas, radius=10, speed=5, x=None, y=None, angle=None):
        self.canvas = canvas
        self.radius = radius
        self.speed = speed
        self.active = True
        
        # Choose a random side and position for the ball to start
        if x is None or y is None:
            side = random.randint(0, 3)  # 0: top, 1: right, 2: bottom, 3: left
            if side == 0:  # top
                x = random.randint(0, canvas.winfo_width())
                y = -radius  # Start outside screen
                angle = random.uniform(math.pi/4, 3*math.pi/4)  # Downward
            elif side == 1:  # right
                x = canvas.winfo_width() + radius
                y = random.randint(0, canvas.winfo_height())
                angle = random.uniform(3*math.pi/4, 5*math.pi/4)  # Leftward
            elif side == 2:  # bottom
                x = random.randint(0, canvas.winfo_width())
                y = canvas.winfo_height() + radius
                angle = random.uniform(5*math.pi/4, 7*math.pi/4)  # Upward
            else:  # left
                x = -radius
                y = random.randint(0, canvas.winfo_height())
                angle = random.uniform(-math.pi/4, math.pi/4)  # Rightward
        
        self.x = x
        self.y = y
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        
        self.ball = canvas.create_oval(
            self.x - radius, self.y - radius,
            self.x + radius, self.y + radius,
            fill='red'
        )

    def move(self):
        # Simple straight movement, no bouncing
        self.x += self.dx
        self.y += self.dy
        
        # Remove if outside screen bounds
        if (self.x + self.radius < 0 or 
            self.x - self.radius > self.canvas.winfo_width() or
            self.y + self.radius < 0 or 
            self.y - self.radius > self.canvas.winfo_height()):
            self.active = False
            self.canvas.delete(self.ball)
            return False
        
        self.canvas.coords(
            self.ball,
            self.x - self.radius,
            self.y - self.radius,
            self.x + self.radius,
            self.y + self.radius
        )
        return True

    def remove(self):
        self.active = False
        self.canvas.delete(self.ball)

class CircleGrid(tk.Canvas):
    def __init__(self, master, grid_type, rows=20, cols=20, circle_radius=15, spacing=30, max_clicks=5,
                 uranium_percent=70, boron_percent=20, reset_from=2, reset_to=30, **kwargs):
        kwargs['width'] = 1900
        kwargs['height'] = 1300
        kwargs['highlightthickness'] = 0
        kwargs['bd'] = 0
        super().__init__(master, **kwargs)
        
        # Colors
        self.uranium_color = "yellow"
        self.boron_color = "#C0C0C0"  # Changed to light gray
        self.empty_color = "black"
        self.clicked_color = "black"
        
        # Configuration
        self.reset_from = reset_from
        self.reset_to = reset_to
        self.uranium_percent = uranium_percent
        self.boron_percent = min(boron_percent, 100 - uranium_percent)  # Ensure percentages don't exceed 100
        self.rows = rows
        self.cols = cols
        self.circle_radius = circle_radius
        self.spacing = spacing
        self.max_clicks = max_clicks
        self.circles = {}
        self.circle_clicks = {}
        self.balls = []
        self.hits_to_white = 5
        self.regeneration_timers = {}  # Add dictionary to track regeneration timers
        self.grid_type = grid_type  # Add grid_type to differentiate between grids
        
        # Add ball counter label
        self.ball_counter = tk.Label(master, text="Balls: 0", font=("Arial", 16), bg="white")
        self.ball_counter.place(x=10, y=10)
        
        # Add boron or uranium control slider based on grid_type
        if grid_type == 'boron':
            self.slider = tk.Scale(
                master,
                from_=100,
                to=0,
                orient=tk.VERTICAL,
                length=300,
                label="Boron %",
                command=self.update_boron_percentage,
                background='white'
            )
            self.slider.set(boron_percent)
            self.slider.place(x=10, y=50)
        elif grid_type == 'uranium':
            self.slider = tk.Scale(
                master,
                from_=100,
                to=0,
                orient=tk.VERTICAL,
                length=300,
                label="Uranium %",
                command=self.update_uranium_percentage,
                background='white'
            )
            self.slider.set(uranium_percent)
            self.slider.place(x=10, y=400)  # Position below the boron slider
        
        # Add reset button
        self.reset_button = tk.Button(
            master,
            text="Reset Ball",
            command=self.reset_ball,
            bg="white",
            font=("Arial", 12)
        )
        self.reset_button.place(x=10, y=360)  # Position below the boron slider
        
        self.after(100, self.create_circles)
        self.after(200, self.create_ball)
        self.after(200, self.update)
        self.bind('<Button-1>', self.on_click)

    def get_color_for_clicks(self, clicks):
        # If not yet at max hits for black, interpolate between yellow and black
        if clicks < self.hits_to_white:
            def hex_to_rgb(hex_color):
                if not hex_color.startswith('#'):
                    temp = tk.Canvas(self)
                    hex_color = temp.winfo_rgb(hex_color)
                    temp.destroy()
                    return tuple(x//256 for x in hex_color)
                return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))

            start_rgb = hex_to_rgb(self.uranium_color)  # Changed from self.main_color
            end_rgb = hex_to_rgb(self.empty_color)     # Already correct
            ratio = clicks / self.hits_to_white
            
            # Calculate intermediate color
            current_rgb = tuple(
                int(start + (end - start) * ratio)
                for start, end in zip(start_rgb, end_rgb)
            )
            
            return f'#{current_rgb[0]:02x}{current_rgb[1]:02x}{current_rgb[2]:02x}'
        else:
            return self.empty_color

    def create_circles(self):
        # Calculate grid size for centering
        grid_width = self.cols * (2 * self.circle_radius + self.spacing)
        grid_height = self.rows * (2 * self.circle_radius + self.spacing)
        
        # Center the grid
        x_start = (self.winfo_width() - grid_width) // 2
        y_start = (self.winfo_height() - grid_height) // 2
        
        # Create grid of circles with alternating uranium and boron lines
        for row in range(self.rows):
            for col in range(self.cols):
                x = x_start + col * (2 * self.circle_radius + self.spacing) + self.circle_radius
                y = y_start + row * (2 * self.circle_radius + self.spacing) + self.circle_radius
                
                tag = f"circle_{row}_{col}"
                if row % 3 == 0:
                    fill_color = self.uranium_color
                elif row % 3 == 1:
                    fill_color = self.boron_color
                else:
                    fill_color = self.empty_color
                
                circle = self.create_oval(
                    x - self.circle_radius,
                    y - self.circle_radius,
                    x + self.circle_radius,
                    y + self.circle_radius,

                    fill=fill_color,
                    tags=(tag,)
                )
                self.circles[tag] = circle
                self.circle_clicks[tag] = 0

    def update_boron_percentage(self, value):
        try:
            new_boron_percent = float(value)
            self.boron_percent = new_boron_percent
            # Clear existing circles and regenerate with new percentage
            for circle_id in self.circles.values():
                self.delete(circle_id)
            self.circles.clear()
            self.circle_clicks.clear()
            self.regeneration_timers.clear()
            self.create_circles()
        except ValueError:
            pass

    def update_uranium_percentage(self, value):
        try:
            new_uranium_percent = float(value)
            self.uranium_percent = new_uranium_percent
            # Clear existing circles and regenerate with new percentage
            for circle_id in self.circles.values():
                self.delete(circle_id)
            self.circles.clear()
            self.circle_clicks.clear()
            self.regeneration_timers.clear()
            self.create_circles()
        except ValueError:
            pass

    def update_ball_counter(self):
        self.ball_counter.config(text=f"Balls: {len(self.balls)}")

    def create_ball(self):
        # Create initial ball with better positioning and speed
        initial_ball = BouncingBall(self, radius=8, speed=15)  # Increased speed
        
        # Calculate grid center
        grid_width = self.cols * (2 * self.circle_radius + self.spacing) - self.spacing
        grid_center_x = self.winfo_width() // 2
        grid_center_y = self.winfo_height() // 2
        
        # Start from left edge at grid's vertical center
        initial_ball.x = 50  # Start a bit inside the window
        initial_ball.y = grid_center_y
        
        # Aim slightly randomly but toward grid center
        angle = random.uniform(-0.2, 0.2)  # Small random angle variation
        initial_ball.dx = math.cos(angle) * initial_ball.speed
        initial_ball.dy = math.sin(angle) * initial_ball.speed
        
        # Update ball position
        self.coords(
            initial_ball.ball,
            initial_ball.x - initial_ball.radius,
            initial_ball.y - initial_ball.radius,
            initial_ball.x + initial_ball.radius,
            initial_ball.y + initial_ball.radius
        )
        
        self.balls = [initial_ball]
        self.update_ball_counter()

    def reset_ball(self):
        # Create a new ball with initial parameters
        initial_ball = BouncingBall(self, radius=8, speed=15)
        
        # Calculate grid center
        grid_width = self.cols * (2 * self.circle_radius + self.spacing) - self.spacing
        grid_center_x = self.winfo_width() // 2
        grid_center_y = self.winfo_height() // 2
        
        # Start from left edge at grid's vertical center
        initial_ball.x = 50
        initial_ball.y = grid_center_y
        
        # Aim slightly randomly but toward grid center
        angle = random.uniform(-0.2, 0.2)
        initial_ball.dx = math.cos(angle) * initial_ball.speed
        initial_ball.dy = math.sin(angle) * initial_ball.speed
        
        # Update ball position
        self.coords(
            initial_ball.ball,
            initial_ball.x - initial_ball.radius,
            initial_ball.y - initial_ball.radius,
            initial_ball.x + initial_ball.radius,
            initial_ball.y + initial_ball.radius
        )
        
        self.balls.append(initial_ball)
        self.update_ball_counter()

    def create_split_balls_from_circle(self, x, y):
        # Create exactly 3 balls shooting out from the grid circle with evenly spaced angles
        angles = [
            random.uniform(0, 2*math.pi/3),           # First third
            random.uniform(2*math.pi/3, 4*math.pi/3), # Second third
            random.uniform(4*math.pi/3, 2*math.pi)    # Last third
        ]
        for angle in angles:
            new_ball = BouncingBall(self, radius=8, speed=3, x=x, y=y, angle=angle)  # Reduced speed from 7 to 3
            self.balls.append(new_ball)
        self.update_ball_counter()

    def update(self):
        # Update all active balls
        for ball in self.balls[:]:  # Use slice copy to allow modification during iteration
            if ball.active:
                if not ball.move():  # Ball hit border
                    self.balls.remove(ball)
                    self.update_ball_counter()
                else:
                    if self.check_collisions(ball):
                        ball.remove()
                        self.balls.remove(ball)
                        self.update_ball_counter()
        
        self.after(16, self.update)

    def check_collisions(self, ball):
        for tag, circle_id in self.circles.items():
            bbox = self.bbox(circle_id)
            if bbox:
                current_color = self.itemcget(circle_id, 'fill')
                
                # Skip if circle is empty/black
                if current_color == self.empty_color:
                    continue
                    
                circle_x = (bbox[0] + bbox[2]) / 2
                circle_y = (bbox[1] + bbox[3]) / 2
                dx = ball.x - circle_x
                dy = ball.y - circle_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < (self.circle_radius + ball.radius):
                    if current_color == self.boron_color:
                        return True
                    
                    if current_color != self.empty_color:  # Changed condition
                        self.circle_clicks[tag] += 1
                        new_color = self.get_color_for_clicks(self.circle_clicks[tag])
                        self.itemconfig(circle_id, fill=new_color)
                        
                        # Start regeneration timer if hits reach max
                        if self.circle_clicks[tag] >= self.hits_to_white:  # Changed from max_clicks
                            self.start_regeneration_timer(tag, circle_id)
                        
                        # Create 3 new red balls when uranium is hit
                        self.create_split_balls_from_circle(circle_x, circle_y)
                        return True
        return False

    def start_regeneration_timer(self, tag, circle_id):
        if tag in self.regeneration_timers:
            self.after_cancel(self.regeneration_timers[tag])
        
        delay = random.randint(int(self.reset_from * 1000), int(self.reset_to * 1000))
        timer_id = self.after(delay, lambda: self.regenerate_uranium(tag, circle_id))
        self.regeneration_timers[tag] = timer_id

    def regenerate_uranium(self, tag, circle_id):
        if tag in self.circle_clicks:  # Add check to ensure tag exists
            self.itemconfig(circle_id, fill=self.uranium_color)
            self.circle_clicks[tag] = 0
            
            if tag in self.regeneration_timers:
                del self.regeneration_timers[tag]

    def on_click(self, event):
        closest = self.find_closest(event.x, event.y)
        if closest:
            x, y = event.x, event.y
            tags = self.gettags(closest[0])
            if tags and tags[0].startswith("circle_"):
                bbox = self.bbox(closest[0])
                if bbox:
                    circle_x = (bbox[0] + bbox[2]) / 2
                    circle_y = (bbox[1] + bbox[3]) / 2
                    # Check if click is within circle radius
                    dx = x - circle_x
                    dy = y - circle_y
                    if math.sqrt(dx*dx + dy*dy) <= self.circle_radius:
                        current_color = self.itemcget(closest[0], 'fill')
                        # Convert color names to RGB values for comparison
                        if self.winfo_rgb(current_color) == self.winfo_rgb(self.empty_color):
                            self.itemconfig(closest[0], fill=self.final_color)
                            # Also update the click count to max to prevent ball interactions
                            tag = tags[0]
                            self.circle_clicks[tag] = self.max_clicks

def main():
    root = tk.Tk()
    root.title("Nuclear Reactor Simulator")
    root.configure(bg='white')  # Set root window background to white

    # Set window size
    window_width = 1900
    window_height = 1300
    
    # Calculate center position for window
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    
    # Set window size and position
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.resizable(False, False)
    
    # Create and place the boron grid
    boron_grid = CircleGrid(
        root,
        grid_type='boron',
        bg="white",
        max_clicks=5,
        uranium_percent=50,  # 50% uranium
        boron_percent=25,    # 25% boron (25% will be empty/black)
        reset_from=2,
        reset_to=30
    )
    boron_grid.place(x=0, y=0, width=950, height=1300)  # Left half of the window
    
    # Create and place the uranium grid
    uranium_grid = CircleGrid(
        root,
        grid_type='uranium',
        bg="white",
        max_clicks=5,
        uranium_percent=50,  # 50% uranium
        boron_percent=25,    # 25% boron (25% will be empty/black)
        reset_from=2,
        reset_to=30
    )
    uranium_grid.place(x=950, y=0, width=950, height=1300)  # Right half of the window
    
    root.mainloop()

if __name__ == "__main__":
    main()