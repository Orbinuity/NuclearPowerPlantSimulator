# Made by Orbinuity company PLEASE read the license
import tkinter as tk
import threading
import random
import time
import math

uranium_heat = {}
is_burned = {}
power_temp = {}
power_temp_val = None
power_procent_val = None

class BouncingBall:
    def __init__(self, canvas, radius=10, speed=5, x=None, y=None, angle=None):
        self.canvas = canvas
        self.radius = radius
        self.speed = speed
        self.active = True

        # Pick a random side for the ball to start
        if x is None or y is None:
            side = random.randint(0, 3)
            if side == 0:  # top
                x = random.randint(0, canvas.winfo_width())
                y = -radius
                angle = random.uniform(math.pi/4, 3*math.pi/4)
            elif side == 1:  # right
                x = canvas.winfo_width() + radius
                y = random.randint(0, canvas.winfo_height())
                angle = random.uniform(3*math.pi/4, 5*math.pi/4)
            elif side == 2:  # bottom
                x = random.randint(0, canvas.winfo_width())
                y = canvas.winfo_height() + radius
                angle = random.uniform(5*math.pi/4, 7*math.pi/4)
            else:  # left
                x = -radius
                y = random.randint(0, canvas.winfo_height())
                angle = random.uniform(-math.pi/4, math.pi/4)
        self.x = x
        self.y = y
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed

        # Create the ball on canvas
        self.ball = canvas.create_oval(
            self.x - radius, self.y - radius,
            self.x + radius, self.y + radius,
            fill='red'
        )

    def move(self):
        # Use canvas.move to shift the ball by dx, dy
        self.canvas.move(self.ball, self.dx, self.dy)
        self.x += self.dx
        self.y += self.dy

        # Check if ball is off-screen
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if (self.x + self.radius < 0 or self.x - self.radius > w or
            self.y + self.radius < 0 or self.y - self.radius > h):
            self.active = False
            self.canvas.delete(self.ball)
            return False
        return True

    def remove(self):
        self.active = False
        self.canvas.delete(self.ball)

class CircleGrid(tk.Canvas):
    def __init__(self, master, rows=20, cols=20, circle_radius=15, spacing=30, max_clicks=5,
                 uranium_percent=70, boron_percent=20, reset_from=2, reset_to=30, output_balls=3,
                 uranium_color="yellow", boron_color="#C0C0C0", empty_color="black", empty_uranium_color="#A9A9A9",
                 do_auto_reset=True, do_manual_reset=True, **kwargs):
        kwargs['width'] = 1900
        kwargs['height'] = 1300
        kwargs['highlightthickness'] = 0
        kwargs['bd'] = 0
        super().__init__(master, **kwargs)
        
        # Colors and settings
        self.uranium_color = uranium_color
        self.boron_color = boron_color
        self.empty_color = empty_color
        self.empty_uranium_color = empty_uranium_color
        self.reset_from = reset_from
        self.reset_to = reset_to
        self.uranium_percent = uranium_percent
        self.live_boron_percent = boron_percent
        self.boron_percent = min(boron_percent, 100 - uranium_percent)
        self.rows = rows
        self.cols = cols
        self.circle_radius = circle_radius
        self.spacing = spacing
        self.max_clicks = max_clicks
        self.output_balls = output_balls
        self.circles = {}
        self.circle_clicks = {}
        self.circle_centers = {}  # Cache circle centers for collision detection
        self.balls = []
        self.hits_to_white = 5
        self.regeneration_timers = {}
        self.do_auto_reset = do_auto_reset
        self.do_manual_reset = do_manual_reset

        # For grid-based collision detection:
        self.cell_size = 2 * self.circle_radius + self.spacing
        self.x_start = None
        self.y_start = None

        # Frame counter (for dynamic collision skipping)
        self.frame_count = 0
        
        # Uranium heat and a lock for thread safety
        self.uranium_heat = {}
        self.uranium_has_count_down = {}

        self._update_called = False

        # For debouncing the slider update:
        self.regen_job = None
        
        # Schedule initialization and update loop
        self.after(100, self.create_circles)
        self.after(200, self.create_ball)
        self.after(66, self.update)  # Try a slower update (~15 FPS) for heavy loads
        self.create_heat()

    def get_color_for_clicks(self, clicks):
        if clicks < self.hits_to_white:
            def hex_to_rgb(hex_color):
                if not hex_color.startswith('#'):
                    temp = tk.Canvas(self)
                    hex_color = temp.winfo_rgb(hex_color)
                    temp.destroy()
                    return tuple(x//256 for x in hex_color)
                return tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            start_rgb = hex_to_rgb(self.uranium_color)
            end_rgb = hex_to_rgb(self.empty_uranium_color)
            ratio = clicks / self.hits_to_white
            current_rgb = tuple(int(start + (end - start) * ratio)
                                for start, end in zip(start_rgb, end_rgb))
            return f'#{current_rgb[0]:02x}{current_rgb[1]:02x}{current_rgb[2]:02x}'
        else:
            return self.empty_uranium_color

    def create_heat(self):
        global uranium_heat
        for row in range(self.rows):
            for col in range(self.cols):
                self.uranium_heat[row, col] = 0
                self.uranium_has_count_down[row, col] = 0
                
                uranium_heat = self.uranium_heat

    def create_circles(self):
        grid_width = self.cols * self.cell_size
        grid_height = self.rows * self.cell_size
        self.x_start = (self.winfo_width() - grid_width) // 2
        self.y_start = (self.winfo_height() - grid_height) // 2

        for row in range(self.rows):
            for col in range(self.cols):
                x = self.x_start + col * self.cell_size + self.circle_radius
                y = self.y_start + row * self.cell_size + self.circle_radius
                
                tag = f"circle_{row}_{col}"

                is_position_1 = (row % 2 == 0 and col % 2 == 0) or (row % 2 == 1 and col % 2 == 1)
                random_value = random.random() * 100
                if is_position_1:
                    fill_color = self.uranium_color if random_value < self.uranium_percent else self.empty_color
                else:
                    fill_color = self.boron_color if random_value < self.boron_percent else self.empty_color
                circle = self.create_oval(
                    x - self.circle_radius, y - self.circle_radius,
                    x + self.circle_radius, y + self.circle_radius,
                    fill=fill_color,
                    tags=(tag,)
                )
                self.circles[tag] = circle
                self.circle_clicks[tag] = 0
                self.circle_centers[tag] = (x, y)

    def update_boron_percentage(self, value):
        try:
            self.boron_percent = 100 - float(value)
            # Use a debounce mechanism: cancel any pending grid regeneration
            if self.regen_job is not None:
                self.after_cancel(self.regen_job)
            # Schedule grid regeneration after 300 ms of inactivity
            self.regen_job = self.after(300, self.regenerate_grid)
        except ValueError:
            pass

    def regenerate_grid(self):
        for circle_id in self.circles.values():
            self.delete(circle_id)
        self.circles.clear()
        self.circle_clicks.clear()
        self.circle_centers.clear()
        self.regeneration_timers.clear()
        self.create_circles()

    def update_ball_counter(self):
        pass

    def create_ball(self):
        initial_ball = BouncingBall(self, radius=8, speed=15)
        grid_center_y = self.winfo_height() // 2
        initial_ball.x = 50
        initial_ball.y = grid_center_y
        angle = random.uniform(-0.2, 0.2)
        initial_ball.dx = math.cos(angle) * initial_ball.speed
        initial_ball.dy = math.sin(angle) * initial_ball.speed
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
        initial_ball = BouncingBall(self, radius=8, speed=15)
        grid_center_y = self.winfo_height() // 2
        initial_ball.x = 50
        initial_ball.y = grid_center_y
        angle = random.uniform(-0.2, 0.2)
        initial_ball.dx = math.cos(angle) * initial_ball.speed
        initial_ball.dy = math.sin(angle) * initial_ball.speed
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
        # Remove any ball exactly at this position
        for ball in self.balls[:]:
            if abs(ball.x - x) < 1 and abs(ball.y - y) < 1:
                ball.remove()
                self.balls.remove(ball)
        new_balls = []
        for i in range(self.output_balls):
            angle = math.radians(random.randint(0, 360))
            new_balls.append(BouncingBall(self, radius=8, speed=3, x=x, y=y, angle=angle))
        self.balls.extend(new_balls)
        self.update_ball_counter()
            
    def config_heat(self, i):
        self.uranium_has_count_down[i] = 1
        var2 = random.randint(10, 20)
        decrement_step = 0.01
        
        var2 = int(var2*self.uranium_heat[i])

        steps = int(self.uranium_heat[i] / decrement_step)
        if steps < 1:
            steps = 1

        for step in range(steps):
            time.sleep(random.randint(abs(var2 - 10), var2 + 10) / steps)
            self.uranium_heat[i] = round(self.uranium_heat[i] - decrement_step, 2)
            if self.uranium_heat[i] < 1:
                break
        self.uranium_has_count_down[i] = 0
        self.uranium_heat[i] = 0

    def update(self):
        global uranium_heat, power_temp_val, power_procent_val
        
        all_temp = 0
        for i in self.uranium_heat:
            all_temp += round(self.uranium_heat[i], 2)
        
        all_temp_dev = 3
        
        uranium_heat = self.uranium_heat
        power_temp_val = round(all_temp/all_temp_dev, 2)
        power_procent_val = len(self.balls)/11.3
    
        start_time = time.perf_counter()
        self.frame_count += 1

        # Determine a collision-skip factor based on the number of balls.
        skip_factor = 3 if len(self.balls) > 20 else 1
        
        if self._update_called:
            for i in self.uranium_heat:
                if self.uranium_has_count_down[i] == 0 and self.uranium_heat[i] > 0:
                    threading.Thread(target=self.config_heat, args=(i,), daemon=True).start()
        else:
            self._update_called = True
            self.create_heat()

        # Process ball movements and collisions
        for ball in self.balls[:]:
            if ball.active:
                if not ball.move():
                    self.balls.remove(ball)
                    self.update_ball_counter()
                else:
                    # Skip collision detection on frames not divisible by skip_factor.
                    if self.frame_count % skip_factor == 0:
                        if self.check_collisions(ball):
                            ball.remove()
                            if ball in self.balls:
                                self.balls.remove(ball)
                            self.update_ball_counter()
        elapsed = time.perf_counter() - start_time
        delay = max(1, 66 - int(elapsed * 1000))  # target ~15 FPS
        self.after(delay, self.update)

    def check_collisions(self, ball):
        if self.x_start is None or self.y_start is None:
            return False
        col_index = int((ball.x - self.x_start) / self.cell_size)
        row_index = int((ball.y - self.y_start) / self.cell_size)
        for r in range(row_index - 1, row_index + 2):
            for c in range(col_index - 1, col_index + 2):
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    tag = f"circle_{r}_{c}"
                    if tag not in self.circles:
                        continue
                    current_color = self.itemcget(self.circles[tag], 'fill')
                    if current_color in (self.empty_color, self.empty_uranium_color):
                        continue
                    cx, cy = self.circle_centers.get(tag, (None, None))
                    if cx is None:
                        continue
                    dx = ball.x - cx
                    dy = ball.y - cy
                    if math.sqrt(dx*dx + dy*dy) < (self.circle_radius + ball.radius):
                        if current_color == self.boron_color:
                            return True
                        self.circle_clicks[tag] += 1
                        new_color = self.get_color_for_clicks(self.circle_clicks[tag])
                        self.itemconfig(self.circles[tag], fill=new_color)
                        if self.circle_clicks[tag] >= self.max_clicks:
                            self.start_regeneration_timer(tag, self.circles[tag])
                        self.create_split_balls_from_circle(cx, cy)
                        self.uranium_heat[r, c] += 1.3
                        return True
        return False

    def start_regeneration_timer(self, tag, circle_id):
        if not self.do_auto_reset:
            return
        if tag in self.regeneration_timers:
            self.after_cancel(self.regeneration_timers[tag])
        delay = random.randint(int(self.reset_from * 1000), int(self.reset_to * 1000))
        timer_id = self.after(delay, lambda: self.regenerate_uranium(tag, circle_id))
        self.regeneration_timers[tag] = timer_id

    def regenerate_uranium(self, tag, circle_id):
        if tag in self.circle_clicks:
            self.itemconfig(circle_id, fill=self.uranium_color)
            self.circle_clicks[tag] = 0

            # Reset the heat for the corresponding grid cell.
            # Extract row and column from tag ("circle_row_col")
            try:
                _, row, col = tag.split('_')
                row, col = int(row), int(col)
                with self.heat_lock:
                    self.uranium_heat[row, col] = 0
                    self.uranium_has_count_down[row, col] = 0
            except Exception:
                pass

            if tag in self.regeneration_timers:
                del self.regeneration_timers[tag]

    def on_click(self, event):
        closest = self.find_closest(event.x, event.y)
        if closest:
            x, y = event.x, event.y
            tags = self.gettags(closest[0])
            if tags and tags[0].startswith("circle_"):
                cx, cy = self.circle_centers.get(tags[0], (None, None))
                if cx is None:
                    return
                if math.sqrt((x-cx)**2 + (y-cy)**2) <= self.circle_radius:
                    current_color = self.itemcget(closest[0], 'fill')
                    if self.do_manual_reset and current_color == self.empty_uranium_color:
                        self.regenerate_uranium(tags[0], closest[0])
                        return
                    if self.winfo_rgb(current_color) == self.winfo_rgb(self.empty_color):
                        self.itemconfig(closest[0], fill=self.uranium_color)
                        self.circle_clicks[tags[0]] = self.max_clicks

class Controlls(tk.Canvas):
    def __init__(self, master, bg="white", circle_grid=None, rows=20, cols=20, circle_radius=15, spacing=30, **kwargs):
        kwargs['width'] = 1900
        kwargs['height'] = 1300
        kwargs['highlightthickness'] = 0
        kwargs['bd'] = 0
        kwargs['bg'] = bg
        super().__init__(master, **kwargs)
        
        self.power_temp = tk.Label(master, text="Heat: 0C", font=("Arial", 16), bg=bg)
        self.power_procent = tk.Label(master, text="Power: 0%", font=("Arial", 16), bg=bg)
        self.slider_label = tk.Label(master, text=" +   Power procent   -", font=("Arial", 12), bg=bg)
        
        self.power_temp.place(x=10, y=10)
        self.power_procent.place(x=10, y=80)
        self.slider_label.place(x=10, y=150)
        
        self.rows = rows
        self.cols = cols
        self.circle_radius = circle_radius
        self.spacing = spacing
        self.cell_size = 2 * self.circle_radius + self.spacing
        self.x_start = None
        self.y_start = None
        self.circles = {}
        self.is_burned = {}
        
        self.boron_slider = tk.Scale(
            master,
            from_=100, to=0,
            orient=tk.HORIZONTAL,
            length=300,
            command=circle_grid.update_boron_percentage,
            background="gray"
        )
        self.boron_slider.set(circle_grid.live_boron_percent)
        self.boron_slider.place(x=10, y=200)
        
        self.reset_button = tk.Button(
            master,
            text="Fire neuron",
            command=circle_grid.reset_ball,
            bg="gray",
            font=("Arial", 12)
        )

        self.reset_button.place(x=10, y=290)
        self.scram_button.place(x=kwargs['width']-150, y=290)
        
        self.after(100, self.create_circles)
        self.after(110, self.update)
        self.bind('<Button-1>', circle_grid.on_click)
        
    def update(self):
        global uranium_heat, power_temp_val, power_procent_val, is_burned
        is_burned = self.is_burned
        
        self.power_temp.config(text=f"Heat: {power_temp_val}C")
        self.power_procent.config(text=f"Power: {round(power_procent_val, 2)}%")
        
        for row in range(self.rows):
            for col in range(self.cols):
                is_position_1 = (row % 2 == 0 and col % 2 == 0) or (row % 2 == 1 and col % 2 == 1)
                if is_position_1:
                    if self.is_burned[row, col] == 0:
                        if uranium_heat[row, col] < 4:
                            self.itemconfig(self.circles[row, col], fill="blue")
                        elif uranium_heat[row, col] > 35 and uranium_heat[row, col] < 50:
                            self.itemconfig(self.circles[row, col], fill="yellow")
                        elif uranium_heat[row, col] > 50 and uranium_heat[row, col] < 90:
                            self.itemconfig(self.circles[row, col], fill="red")
                        elif uranium_heat[row, col] > 90:
                            self.itemconfig(self.circles[row, col], fill="black")
                            self.is_burned[row, col] = 1
                        else:
                            self.itemconfig(self.circles[row, col], fill="green")
                    else:
                        self.itemconfig(self.circles[row, col], fill="black")
        self.after(66, self.update)
        
    def create_circles(self):
        grid_width = self.cols * self.cell_size
        grid_height = self.rows * self.cell_size
        self.x_start = (self.winfo_width() - grid_width) // 2
        self.y_start = (self.winfo_height() - grid_height) // 2

        for row in range(self.rows):
            for col in range(self.cols):
                x = self.x_start + col * self.cell_size + self.circle_radius
                y = self.y_start + row * self.cell_size + self.circle_radius

                is_position_1 = (row % 2 == 0 and col % 2 == 0) or (row % 2 == 1 and col % 2 == 1)
                if is_position_1:
                    self.is_burned[row, col] = 0
                    self.circles[row, col] = self.create_oval(
                        x - self.circle_radius, y - self.circle_radius,
                        x + self.circle_radius, y + self.circle_radius,
                        fill="orange"
                    )
        
def main():
    root = tk.Tk()
    root.title("Nuclear Reactor")
    root.configure(bg='#ADD8E6')
    window_width = 1900
    window_height = 1300
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    root.resizable(False, False)
    
    win2 = tk.Tk()
    win2.title("Nuclear Reactor Controler")
    win2.configure(bg='#ADD8E6')
    win2_window_width = 1900
    win2_window_height = 1300
    win2_screen_width = root.winfo_screenwidth()
    win2_screen_height = root.winfo_screenheight()
    win2_center_x = int(win2_screen_width/2 - win2_window_width/2)
    win2_center_y = int(win2_screen_height/2 - win2_window_height/2)
    win2.geometry(f'{win2_window_width}x{win2_window_height}+{win2_center_x}+{win2_center_y}')
    win2.resizable(True, True)
    
    circle_grid = CircleGrid(
        root,
        bg="#ADD8E6",
        output_balls=3,
        uranium_percent=100,
        boron_percent=50,
        reset_from=2,
        reset_to=10,
        uranium_color="yellow",
        boron_color="#C0C0C0",
        empty_color="black",
        empty_uranium_color="white",
        do_auto_reset=True,
        do_manual_reset=False,
    )
    
    controlls = Controlls(
        win2,
        bg="#ADD8E6",
        circle_grid=circle_grid
    )
    
    circle_grid.pack(fill="both", expand=True, padx=0, pady=0)
    controlls.pack(fill="both", expand=True, padx=0, pady=0)
    
    root.mainloop()
    win2.mainloop()

if __name__ == "__main__":
    main()

