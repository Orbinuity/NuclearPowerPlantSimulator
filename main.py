# Made by Orbinuity company PLEASE read the license
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
    def __init__(self, master, rows=20, cols=20, circle_radius=15, spacing=30, max_clicks=5,
                 uranium_percent=70, boron_percent=20, reset_from=2, reset_to=30, output_balls=3,
                 uranium_color = "yellow", boron_color = "#C0C0C0", empty_color = "black", empty_uranium_color = "#A9A9A9",
                 do_auto_reset=True, do_manual_reset=True, **kwargs):
        kwargs['width'] = 1900
        kwargs['height'] = 1300
        kwargs['highlightthickness'] = 0
        kwargs['bd'] = 0
        super().__init__(master, **kwargs)
        
        # Colors
        self.uranium_color = uranium_color
        self.boron_color = boron_color # Changed to light gray
        self.empty_color = empty_color
        self.empty_uranium_color = empty_uranium_color
        
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
        self.output_balls = output_balls  # New variable for number of output balls
        self.circles = {}
        self.circle_clicks = {}
        self.balls = []
        self.hits_to_white = 5
        self.regeneration_timers = {}  # Add dictionary to track regeneration timers
        self.do_auto_reset = do_auto_reset
        self.do_manual_reset = do_manual_reset
        
        # Add ball counter label
        self.ball_counter = tk.Label(master, text="Balls: 0", font=("Arial", 16), bg="white")
        self.ball_counter.place(x=10, y=10)
        
        # Only keep boron control slider
        self.boron_slider = tk.Scale(
            master,
            from_=100,
            to=0,
            orient=tk.VERTICAL,
            length=300,
            label="Boron %",
            command=self.update_boron_percentage,
            background='white'
        )
        self.boron_slider.set(boron_percent)
        self.boron_slider.place(x=10, y=50)
        
        # Add reset button
        self.reset_button = tk.Button(
            master,
            text="Reset Ball",
            command=self.reset_ball,
            bg="white",
            font=("Arial", 12)
        )
        self.reset_button.place(x=10, y=360)
        
        self.after(100, self.create_circles)
        self.after(200, self.create_ball)
        self.after(200, self.update)
        self.bind('<Button-1>', self.on_click)

        self.cube_color = "#0000FF"  # Bright blue for cubes
        self.cube_heat_color = "#FF0000"  # Bright red for heated cubes
        self.heat_steps = 5  # Number of hits needed for full red
        self.cubes = {}  # Store cube IDs
        self.cube_temps = {}  # Store cube temperatures (0.0 to 1.0)
        self.heat_spread_radius = 3  # Reduced from 5 to 3
        self.heat_falloff = 0.7  # Increased from 0.5 to 0.7 for faster falloff
        self.cooling_base_rate = 0.001  # Much slower cooling (was 0.01)
        self.cooling_interval = 100  # Longer interval between cooling steps (was 50)

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
            end_rgb = hex_to_rgb(self.empty_uranium_color)     # Already correct
            ratio = clicks / self.hits_to_white
            
            # Calculate intermediate color
            current_rgb = tuple(
                int(start + (end - start) * ratio)
                for start, end in zip(start_rgb, end_rgb)
            )
            
            return f'#{current_rgb[0]:02x}{current_rgb[1]:02x}{current_rgb[2]:02x}'
        else:
            return self.empty_uranium_color

    def create_circles(self):
        # Calculate grid size for centering
        grid_width = self.cols * (2 * self.circle_radius + self.spacing)
        grid_height = self.rows * (2 * self.circle_radius + self.spacing)
        
        # Center the grid
        x_start = (self.winfo_width() - grid_width) // 2
        y_start = (self.winfo_height() - grid_height) // 2
        
        # Create checkerboard pattern with random empty spaces based on percentages
        for row in range(self.rows):
            for col in range(self.cols):
                x = x_start + col * (2 * self.circle_radius + self.spacing) + self.circle_radius
                y = y_start + row * (2 * self.circle_radius + self.spacing) + self.circle_radius
                
                tag = f"circle_{row}_{col}"
                cube_tag = f"cube_{row}_{col}"
                
                # Create larger background cube
                cube_size = self.circle_radius * 3.0  # Make cubes bigger
                cube = self.create_rectangle(
                    x - cube_size/2, y - cube_size/2,
                    x + cube_size/2, y + cube_size/2,
                    fill=self.cube_color,
                    tags=(cube_tag,)
                )
                self.cubes[cube_tag] = cube
                self.cube_temps[cube_tag] = 0.0
                
                # Determine pattern position (1 or 2)
                is_position_1 = (row % 2 == 0 and col % 2 == 0) or (row % 2 == 1 and col % 2 == 1)
                
                # Apply percentages to determine if circle should be empty
                random_value = random.random() * 100
                if is_position_1:
                    fill_color = (self.uranium_color if random_value < self.uranium_percent 
                                else self.empty_color)
                else:
                    fill_color = (self.boron_color if random_value < self.boron_percent 
                                else self.empty_color)
                
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
            self.regenerate_grid()
        except ValueError:
            pass

    def regenerate_grid(self):
        # Clear existing circles
        for circle_id in self.circles.values():
            self.delete(circle_id)
        self.circles.clear()
        self.circle_clicks.clear()
        self.regeneration_timers.clear()
        # Clear existing cubes as well
        for cube_id in self.cubes.values():
            self.delete(cube_id)
        self.cubes.clear()
        self.cube_temps.clear()
        # Create new grid
        self.create_circles()

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
        # Create exactly 2 balls in opposite directions, no more
        # Clear all existing balls at this location first
        for ball in self.balls[:]:
            if abs(ball.x - x) < 1 and abs(ball.y - y) < 1:
                ball.remove()
                self.balls.remove(ball)
        
        # Fixed angles for consistent behavior: right and left
        # Create exactly 2 balls
        new_balls = []

        for i in range(self.output_balls):
            new_balls.append(BouncingBall(self, radius=8, speed=3, x=x, y=y, angle=random.randint(0,360)))
        
        self.balls.extend(new_balls)
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
                if current_color == self.empty_color or current_color == self.empty_uranium_color:
                    continue
                    
                circle_x = (bbox[0] + bbox[2]) / 2
                circle_y = (bbox[1] + bbox[3]) / 2
                dx = ball.x - circle_x
                dy = ball.y - circle_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance < (self.circle_radius + ball.radius):
                    if current_color == self.boron_color:
                        return True
                    
                    if current_color != self.empty_color and current_color != self.empty_uranium_color:
                        self.circle_clicks[tag] += 1
                        new_color = self.get_color_for_clicks(self.circle_clicks[tag])
                        self.itemconfig(circle_id, fill=new_color)
                        
                        if self.circle_clicks[tag] >= self.max_clicks:
                            self.start_regeneration_timer(tag, circle_id)
                        
                        # Heat up the cube when uranium is hit
                        cube_tag = f"cube_{tag.split('_')[1]}_{tag.split('_')[2]}"
                        self.heat_cube(cube_tag)
                        
                        # Create exactly two balls
                        self.create_split_balls_from_circle(circle_x, circle_y)
                        return True
        return False

    def start_regeneration_timer(self, tag, circle_id):
        if not self.do_auto_reset:
            return  # Don't start timer if auto-reset is disabled
            
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

    def heat_cube(self, cube_tag):
        # Parse row and col from cube tag
        _, row, col = cube_tag.split('_')
        row, col = int(row), int(col)
        
        # Heat center cube fully
        self.cube_temps[cube_tag] = 1.0
        self.update_cube_color(cube_tag)
        
        # Heat surrounding cubes with diminishing effect in a larger radius
        for r in range(-self.heat_spread_radius, self.heat_spread_radius + 1):
            for c in range(-self.heat_spread_radius, self.heat_spread_radius + 1):
                if r == 0 and c == 0:
                    continue  # Skip center cube (already handled)
                
                neighbor_row = row + r
                neighbor_col = col + c
                
                if 0 <= neighbor_row < self.rows and 0 <= neighbor_col < self.cols:
                    neighbor_tag = f"cube_{neighbor_row}_{neighbor_col}"
                    if neighbor_tag in self.cube_temps:
                        # Calculate distance-based heat with gentler falloff
                        distance = math.sqrt(r*r + c*c)
                        heat = max(0, 1 - (distance / self.heat_spread_radius) * self.heat_falloff)
                        # Add heat to neighbor
                        current_temp = self.cube_temps[neighbor_tag]
                        self.cube_temps[neighbor_tag] = max(current_temp, heat)
                        self.update_cube_color(neighbor_tag)
                        # Start cooling for neighbor
                        self.after(50, lambda t=neighbor_tag: self.cool_cube(t))
        
        # Start cooling for center cube
        self.after(50, lambda: self.cool_cube(cube_tag))

    def cool_cube(self, cube_tag):
        if self.cube_temps[cube_tag] > 0:
            _, row, col = cube_tag.split('_')
            row, col = int(row), int(col)
            
            # Calculate cooling rate based on neighbors
            total_temp = 0
            neighbor_count = 0
            
            for r in range(-1, 2):
                for c in range(-1, 2):
                    if r == 0 and c == 0:
                        continue
                    
                    neighbor_row = row + r
                    neighbor_col = col + c
                    
                    if 0 <= neighbor_row < self.rows and 0 <= neighbor_col < self.cols:
                        neighbor_tag = f"cube_{neighbor_row}_{neighbor_col}"
                        if neighbor_tag in self.cube_temps:
                            total_temp += self.cube_temps[neighbor_tag]
                            neighbor_count += 1
            
            # Cool much slower than before
            if neighbor_count > 0:
                avg_temp = total_temp / neighbor_count
                cooling_rate = self.cooling_base_rate * (1 + (self.cube_temps[cube_tag] - avg_temp))
            else:
                cooling_rate = self.cooling_base_rate
            
            self.cube_temps[cube_tag] = max(0.0, self.cube_temps[cube_tag] - cooling_rate)
            self.update_cube_color(cube_tag)
            
            if self.cube_temps[cube_tag] > 0:
                self.after(self.cooling_interval, lambda: self.cool_cube(cube_tag))

    def update_cube_color(self, cube_tag):
        # Smoother color interpolation between blue and red
        temp = self.cube_temps[cube_tag]
        
        # Start from blue (0,0,255) to red (255,0,0)
        r = int(255 * temp)
        b = int(255 * (1-temp))
        color = f"#{r:02x}00{b:02x}"
        
        self.itemconfig(self.cubes[cube_tag], fill=color)

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
                        
                        # Handle manual reset of depleted uranium
                        if self.do_manual_reset and current_color == self.empty_uranium_color:
                            self.regenerate_uranium(tags[0], closest[0])
                            return
                        
                        # Original click handling
                        if self.winfo_rgb(current_color) == self.winfo_rgb(self.empty_color):
                            self.itemconfig(closest[0], fill=self.final_color)
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
    
    # Create and place the circle grid with no padding
    circle_grid = CircleGrid(
        root,
        bg="white",
        output_balls=3,
        uranium_percent=50,
        boron_percent=10,
        reset_from=2,
        reset_to=30,
        uranium_color="yellow",
        boron_color="#C0C0C0",
        empty_color="black",
        empty_uranium_color="white",
        do_auto_reset=False,
        do_manual_reset=True
    )
    
    # Fill the entire window with the canvas
    circle_grid.pack(fill="both", expand=True, padx=0, pady=0)
    
    root.mainloop()

if __name__ == "__main__":
    main()