import arcade
import random
import timeit
import math
import os

#Window Constraints
screen_title = 'Grick Rimes: Zombie Slayer'
screen_width = 1920
screen_height = 1080

player_health = 100

title_scaling = .5

#Scaling
#Smaller number, more map is visible
wall_scale = .5
player_scale = .4
wall_size = int(128 * wall_scale)

grid_width = 50
grid_height = 50

area_width = grid_width*wall_size
area_height = grid_height * wall_size

viewpoint_margin = 500

merge_sprites = False
movement_speed = 5

class Room:
    def __init__(self,r,c,h,w):
        self.row = r
        self.col = c
        self.height = h
        self.width = w

class MapGenerator:
    def __init__(self,w,h):
        self.maxsections = 15
        self.width = w
        self.height = h
        self.leaves = []
        self.dungeon = []
        self.rooms = []

        for h in range(self.height):
            row = []
            for w in range(self.width):
                row.append('#')
            self.dungeon.append(row)

    def random_split(self,min_row,min_col,max_row,max_col):
        #Split until we get to the max threshold (maxsections)
        seg_height = max_row - min_row
        seg_width = max_col - min_col

        if seg_height < self.maxsections and seg_width < self.maxsections:
            self.leaves.append((min_row, min_col, max_row, max_col))
        elif seg_height < self.maxsections <= seg_width:
            self.split_on_vertical(min_row, min_col, max_row, max_col)
        elif seg_height >= self.maxsections > seg_width:
            self.split_on_horizontal(min_row, min_col, max_row, max_col)
        else:
            if random.random() < .5:
                self.split_on_horizontal(min_row,min_col,max_row,max_col)
            else:
                self.split_on_vertical(min_row,min_col,max_row,max_col)
    
    def split_on_horizontal(self, min_row, min_col, max_row, max_col):
        split = (min_row + max_row) // 2 + random.choice((-2,-1,0,1,2))
        self.random_split(min_row, min_col, split, max_col)
        self.random_split(split + 1, min_col, max_row, max_col)

    def split_on_vertical(self, min_row, min_col, max_row, max_col):
        split = (min_col + max_col) // 2 + random.choice((-2,-1,0,1,2))
        self.random_split(min_row, min_col, max_row, split)
        self.random_split(min_row, split + 1, max_row, max_col)

    def carve_rooms(self):
        for leaf in self.leaves:
            #random chance room is carved, so rooms are more unique
            if random.random() > .80:
                continue
            section_width = leaf[3] - leaf[1]
            section_height = leaf[2] - leaf[0]

            room_width = round(random.randrange(40,100) / 100 * section_width)
            room_height = round(random.randrange(40,100) / 100 * section_height)

            #Adjust room size if there is space

            if section_height > room_height:
                room_start_row = leaf[0] + random.randrange(section_height - room_height)
            else:
                room_start_row = leaf[0]
            
            if section_width > room_width:
                room_start_col = leaf[1] + random.randrange(section_width - room_width)
            else:
                room_start_col = leaf[1]
            
            self.rooms.append(Room(room_start_row, room_start_col, room_height, room_width))
            for r in range(room_start_row, room_start_row + room_height):
                for c in range(room_start_row, room_start_col + room_width):
                    self.dungeon[r][c] = '.'
    
    @staticmethod
    def adjacent_rooms(room1,room2):
        #Checks if rooms are next to eachother
        adj_rows = []
        adj_cols = []
        for r in range(room1.row, room1.row + room1.height):
            if room2.row <= r < room2.row + room2.height:
                adj_rows.append(r)
        
        for c in range(room1.col, room1.col + room1.width):
            if room2.col <= c < room2.col + room2.width:
                adj_cols.append(c)
        
        return adj_rows, adj_cols

    @staticmethod
    def room_distance(room1,room2):
        center1 = (room1.row + room1.height // 2, room1.col + room1.width // 2)
        center2 = (room2.row + room2.height // 2, room2.col + room2.width // 2)

        return math.sqrt((center1[0] - center2[0]) ** 2 + (center1[1] - center2[1]) ** 2)

    def carve_hallway(self, room1, room2):
        #Makes a hallway between rooms
        if room2[2] == 'rows':
            row = random.choice(room2[1])
            if room1.col + room1.width < room2[0].col:
                start_col = room1.col + room1.width
                end_col = room2[0].col
            else:
                start_col = room2[0].col + room2[0].width
                end_col = room1.col
            for c in range(start_col, end_col):
                self.dungeon[row][c] = '.'
            
            if end_col - start_col >= 4:
                self.dungeon[row][start_col] = '+'
                self.dungeon[row][end_col - 1] = '+'
            elif start_col == end_col - 1:
                self.dungeon[row][start_col] = '+'
        else:
            col = random.choice(room2[1])
            if room1.row + room1.height < room2[0].row:
                start_row = room1.row + room1.height
                end_row = room2[0].row
            else:
                start_row = room2[0].row + room2[0].height
                end_row = room1.row
            for r in range(start_row, end_row):
                self.dungeon[r][col] = '.'
            
            if end_row - start_row >= 4:
                self.dungeon[start_row][col] = '+'
                self.dungeon[end_row-1][col] = '+'
            elif start_row == end_row - 1:
                self.dungeon[start_row][col] = '+'


    def find_closest_unconnected_rooms(self, groups, room_dict):
        #Finds 2 rooms that are in different groups and connects them
        
        shortest_distance = 99999
        start = None
        start_group = None
        nearest = None

        for group in groups:
            for room in group:
                key = (room.row, room.col)
                for other in room_dict[key]:
                    if not other[0] in group and other[3] < shortest_distance:
                        shortest_distance = other[3]
                        start = room
                        nearest = other
                        start_group = group
        self.carve_hallway(start, nearest)

        #Merge the groups
        other_group = None
        for group in groups:
            if nearest[0] in group:
                other_group = group
                break
        
        start_group += other_group
        groups.remove(other_group)

    def connect_rooms(self):
        groups = []
        room_dict = {}
        for room in self.rooms:
            key = (room.row, room.col)
            room_dict[key] = []
            for other in self.rooms:
                other_key = (other.row, other.col)
                if key == other_key:
                    continue
                adj = self.adjacent_rooms(room,other)
                if len(adj[0]) > 0:
                    room_dict[key].append((other, adj[0], 'rows', self.room_distance(room, other)))
                elif len(adj[1]) > 0:
                    room_dict[key].append((other, adj[1], 'cols', self.room_distance(room, other)))

            groups.append([room])

        while len(groups) > 1:
            self.find_closest_unconnected_rooms(groups, room_dict)

    def generate_map(self):
        self.random_split(1, 1, self.height -1, self.width - 1)
        self.carve_rooms()
        self.connect_rooms()
        
class MyGame(arcade.Window):
    #Main Application

    def __init__(self, width, height, title):
        super().__init__(width, height, title)
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)
        self.window = self

        self.shoot_pressed = False
        self.can_shoot = False
        self.shoot_timer = 0

        self.grid = None 
        self.wall_list = None
        self.player_list = None
        self.player_sprite = None
        self.zombie_list = None
        self.zombie_sprite = None
        self.zombie_count = 0

        self.view_bottom = 0
        self.view_left = 0
        self.physics_engine = None

        self.processing_time = 0 
        self.draw_time = 0

        self.set_mouse_visible(False)
        audio = arcade.load_sound('Jeremy Blake - Powerup!.mp3')
        arcade.play_sound(audio,1.0,True)
        arcade.set_background_color(arcade.color.DARK_ORANGE)

    def setup(self):
        self.wall_list = arcade.SpriteList(use_spatial_hash = True)
        self.player_list = arcade.SpriteList()
        self.zombie_list = arcade.SpriteList()

        dg = MapGenerator(grid_width, grid_height)
        dg.generate_map()

        self.can_shoot = True
        self.shoot_timer = 0

        self.scene.add_sprite(LAYER_NAME_BULLETS)

        if not merge_sprites:
            for row in range(dg.height):
                for column in range(dg.width):
                    value = dg.dungeon[row][column]
                    if value == '#':
                        wall = arcade.Sprite('wall_new.png', wall_scale)
                        wall.center_x = column * wall_size + wall_size / 2
                        wall.center_y = row * wall_size + wall_size / 2
                        self.wall_list.append(wall)

        else:
            for row in range(dg.height):
                column = 0 
                while column < dg.width:
                    while column < dg.width and dg.dungeon[row][row] != '#':
                        column += 1
                    start_column = column
                    while column < dg.width and dg.dungeon[row][column] == '#':
                        column += 1
                    end_column = column

                    column_count = end_column - start_column + 1
                    column_mid = (start_column + end_column) / 2

                    wall = arcade.Sprite('wall_new.png', wall_scale, repeat_count_x = column_count)
                    wall.center_x = column_mid * wall_size + wall_size / 2
                    wall.center_y = row * wall_size + wall_size / 2
                    wall.width = wall_size * column_count
                    self.wall_list.append(wall)
        self.player_sprite = arcade.Sprite('GrickRimes.png', player_scale)
        self.player_list.append(self.player_sprite)

        placed = False
        while not placed:

            self.player_sprite.center_x = random.randrange(area_width)
            self.player_sprite.center_y = random.randrange(area_height)

            walls_hit = arcade.check_for_collision_with_list(self.player_sprite, self.wall_list)
            if len(walls_hit) == 0:
                placed = True
        
        self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.wall_list)

    def on_draw(self):
        global player_health


        draw_start_time = timeit.default_timer()

        self.clear()

        self.wall_list.draw()
        self.player_list.draw()
        self.zombie_list.draw()

        sprite_count = len(self.wall_list)

        player_health_display = f'Health: {player_health}'
        arcade.draw_text(player_health_display, self.view_left + 20, screen_height -120 + self.view_bottom, arcade.color.WHITE, 16)

        output = f'Sprite Count: {sprite_count}'
        arcade.draw_text(output, self.view_left + 20, screen_height - 60 + self.view_bottom, arcade.color.WHITE, 16)

        self.draw_time = timeit.default_timer() - draw_start_time
    
    def on_key_press(self, key, modifiers):

        if key == arcade.key.UP:
            self.player_sprite.change_y = movement_speed
        elif key == arcade.key.DOWN:
            self.player_sprite.change_y = -movement_speed
        elif key == arcade.key.LEFT:
            self.player_sprite.change_x = -movement_speed
        elif key == arcade.key.RIGHT:
            self.player_sprite.change_x = movement_speed

        if key == arcade.key.SPACE:
            self.shoot_pressed = True

        self.process_keychange()

    def on_key_release(self, key, modifiers):

        if key == arcade.key.UP or key == arcade.key.DOWN:
            self.player_sprite.change_y = 0
        elif key == arcade.key.LEFT or key == arcade.key.RIGHT:
            self.player_sprite.change_x = 0

        if key == arcade.key.SPACE:
            self.shoot_pressed = False

            self.process_keychange()

    def spawn_zombie(self):
        chance = random.randint(0,10)
        if chance > 7:
            self.zombie_sprite = arcade.Sprite('me_real.png', player_scale)
        else:
            self.zombie_sprite = arcade.Sprite('zombie_real.png', player_scale)
        self.zombie_list.append(self.zombie_sprite)
        print('spawning zombie')
        placed = False
        while not placed:

            self.zombie_sprite.center_x = random.randrange(area_width)
            self.zombie_sprite.center_y = random.randrange(area_height)

            walls_hit = arcade.check_for_collision_with_list(self.zombie_sprite, self.wall_list)
            if len(walls_hit) == 0:
                placed = True
        
        #self.physics_engine = arcade.PhysicsEngineSimple(self.zombie_sprite, self.wall_list)

    def on_update(self, delta_time):
        global player_health
        zombie_spawn = random.randint(0,1000)
        zombie_speed = random.randint(1,3)

        self.physics_engines = []

        if self.can_shoot:
            if self.shoot_pressed:
                bullet = arcade.Sprite('bullet.png')

        for zombie in self.zombie_list:
            physics_engine = arcade.PhysicsEngineSimple(zombie, self.wall_list)
            self.physics_engines.append(physics_engine)

        for physics_engine in self.physics_engines:
            physics_engine.update()

        collision_zombie = arcade.check_for_collision_with_list(self.player_sprite, self.zombie_list)
        
        # If the list is not empty, the player and a zombie have collided
        if collision_zombie:
            print('taking damage')
            player_health -= 1

        if player_health == 0:
            print('player lost')
            self.window.close()
        if self.zombie_count < 5:
            if zombie_spawn > 100 and zombie_spawn < 105:
                self.spawn_zombie()
                self.zombie_count += 1
        elif self.zombie_count < 20:
            if zombie_spawn > 100 and zombie_spawn < 110:
                print('over 5')
                self.spawn_zombie()
                self.zombie_count += 1

        for zombie in self.zombie_list:
            if zombie.center_y < self.player_sprite.center_y:
                zombie.center_y += min(zombie_speed, self.player_sprite.center_y - zombie.center_y)
            elif zombie.center_y > self.player_sprite.center_y:
                zombie.center_y -= min(zombie_speed, zombie.center_y - self.player_sprite.center_y)

            if zombie.center_x < self.player_sprite.center_x:
                zombie.center_x += min(zombie_speed, self.player_sprite.center_x - zombie.center_x)
            elif zombie.center_x > self.player_sprite.center_x:
                zombie.center_x -= min(zombie_speed, zombie.center_x - self.player_sprite.center_x)

        start_time = timeit.default_timer()
        self.physics_engine.update()

        changed = False

        left_bndry = self.view_left + viewpoint_margin
        if self.player_sprite.left < left_bndry:
            self.view_left -= left_bndry - self.player_sprite.left
            changed = True
        
        right_bndry = self.view_left + screen_width - viewpoint_margin
        if self.player_sprite.right > right_bndry:
            self.view_left+= self.player_sprite.right - right_bndry
            changed = True

        top_bndry = self.view_bottom + screen_height - viewpoint_margin
        if self.player_sprite.top > top_bndry:
            self.view_bottom += self.player_sprite.top - top_bndry
            changed = True

        bottom_bndry = self.view_bottom + viewpoint_margin
        if self.player_sprite.bottom < bottom_bndry:
            self.view_bottom -= bottom_bndry - self.player_sprite.bottom
            changed = True

        if changed:
            arcade.set_viewport(self.view_left, screen_width + self.view_left, self.view_bottom, screen_height + self.view_bottom)

            self.processing_time = timeit.default_timer() - start_time

global zombie_counter
def main():
    game = MyGame(screen_width, screen_height, screen_title)
    game.setup()
    arcade.run()

main()