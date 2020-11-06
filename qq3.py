
import configparser
#py -m pip install networkx #code to install in window console
import networkx as nx
import pygame
import pygame.locals as pg

# Motion offsets for particular directions
#     N  E  S   W
DX = [0, 1, 0, -1]
DY = [-1, 0, 1, 0]

# Dimensions of the map tiles
MAP_TILE_WIDTH, MAP_TILE_HEIGHT = 24, 16

class TileCache(object):

    """Load the tilesets lazily into global cache"""

    def __init__(self,  width=32, height=None):
        self.width = width
        self.height = height or width
        self.cache = {}
    
    def __getitem__(self, filename):
        """Return a table of tiles, load it from disk if needed."""

        key = (filename, self.width, self.height)
        try:
            return self.cache[key]
        except KeyError:
            tile_table = self._load_tile_table(filename, self.width,
                                               self.height)
            self.cache[key] = tile_table
            return tile_table

    def _load_tile_table(self, filename, width, height):
        """Load an image and split it into tiles."""

        image = pygame.image.load(filename).convert()
        image_width, image_height = image.get_size()
        tile_table = []
        for tile_x in range(0, image_width // width):
            line = []
            tile_table.append(line)
            for tile_y in range(0, image_height // height):
                rect = (tile_x*width, tile_y*height, width, height)
                line.append(image.subsurface(rect))
        return tile_table


class SortedUpdates(pygame.sprite.RenderUpdates):
    """A sprite group that sorts them by depth."""

    def sprites(self):
        """The list of sprites in the group, sorted by depth."""

        return sorted(list(self.spritedict.keys()), key=lambda sprite: sprite.depth)


class Shadow(pygame.sprite.Sprite):
    """Sprite for shadows."""

    def __init__(self, owner):
        pygame.sprite.Sprite.__init__(self)
        self.image = SPRITE_CACHE["shadow.png"][0][0]
        self.image.set_alpha(64)
        self.rect = self.image.get_rect()
        self.owner = owner

    def update(self, *args):
        """Make the shadow follow its owner."""

        self.rect.midbottom = self.owner.rect.midbottom


class Sprite(pygame.sprite.Sprite):
    """Sprite for animated items and base class for Player."""

    is_player = False

    def __init__(self, pos=(0, 0), frames=None):
        super(Sprite, self).__init__()
        if frames:
            self.frames = frames
        self.image = self.frames[0][0]
        self.rect = self.image.get_rect()
        self.animation = self.stand_animation()
        self.pos = pos

    def _get_pos(self):
        """Check the current position of the sprite on the map."""

        return ((self.rect.midbottom[0] - 12) // 24,
                (self.rect.midbottom[1] - 16) // 16)

    def _set_pos(self, pos):
        """Set the position and depth of the sprite on the map."""

        self.rect.midbottom = pos[0]*24+12, pos[1]*16+16
        self.depth = self.rect.midbottom[1]

    pos = property(_get_pos, _set_pos)

    def move(self, dx, dy):
        """Change the position of the sprite on screen."""

        self.rect.move_ip(dx, dy)
        self.depth = self.rect.midbottom[1]

    def stand_animation(self):
        """The default animation."""

        while True:
            # Change to next frame every two ticks
            for frame in self.frames[0]:
                self.image = frame
                yield None
                yield None

    def update(self, *args):
        """Run the current animation."""

        next(self.animation)


class Player(Sprite):
    """ Display and animate the player character."""

    is_player = True

    def __init__(self, pos=(1, 1)):
        self.frames = SPRITE_CACHE["player.png"]
        Sprite.__init__(self, pos)
        self.direction = 2
        self.animation = None
        self.image = self.frames[self.direction][0]

    def walk_animation(self):
        """Animation for the player walking."""

        # This animation is hardcoded for 4 frames and 16x24 map tiles
        for frame in range(4):
            self.image = self.frames[self.direction][frame]
            yield None
            self.move(3*DX[self.direction], 2*DY[self.direction])
            yield None
            self.move(3*DX[self.direction], 2*DY[self.direction])

    def update(self, *args):
        """Run the current animation or just stand there if no animation set."""

        if self.animation is None:
            self.image = self.frames[self.direction][0]
        else:
            try:
                next(self.animation)
            except StopIteration:
                self.animation = None


class Level(object):
    """Load and store the map of the level, together with all the items."""

    def __init__(self, filename="level.map"):
        self.tileset = ''
        self.map = []
        self.items = {}
        self.key = {}
        self.width = 0
        self.height = 0
        self.load_file(filename)

    def load_file(self, filename="level.map"):
        """Load the level from specified file."""

        parser = configparser.ConfigParser()
        parser.read(filename)
        self.tileset = parser.get("level", "tileset")
        self.map = parser.get("level", "map").split("\n")
        for section in parser.sections():
            if len(section) == 1:
                desc = dict(parser.items(section))
                self.key[section] = desc

        self.width = len(self.map[0])
        self.height = len(self.map)
        for y, line in enumerate(self.map):
            for x, c in enumerate(line):
                if not self.is_wall(x, y) and 'sprite' in self.key[c]:
                    self.items[(x, y)] = self.key[c]
                

    def render(self):
        """Draw the level on the surface."""

        wall = self.is_wall
        tiles = MAP_CACHE[self.tileset]
        image = pygame.Surface((self.width*MAP_TILE_WIDTH, self.height*MAP_TILE_HEIGHT))
        overlays = {}
        for map_y, line in enumerate(self.map):
            for map_x, c in enumerate(line):
                if wall(map_x, map_y):
                    # Draw different tiles depending on neighbourhood
                    if not wall(map_x, map_y+1):
                        if wall(map_x+1, map_y) and wall(map_x-1, map_y):
                            tile = 1, 2
                        elif wall(map_x+1, map_y):
                            tile = 0, 2
                        elif wall(map_x-1, map_y):
                            tile = 2, 2
                        else:
                            tile = 3, 2
                    else:
                        if wall(map_x+1, map_y+1) and wall(map_x-1, map_y+1):
                            tile = 1, 1
                        elif wall(map_x+1, map_y+1):
                            tile = 0, 1
                        elif wall(map_x-1, map_y+1):
                            tile = 2, 1
                        else:
                            tile = 3, 1
                    # Add overlays if the wall may be obscuring something
                    if not wall(map_x, map_y-1):
                        if wall(map_x+1, map_y) and wall(map_x-1, map_y):
                            over = 1, 0
                        elif wall(map_x+1, map_y):
                            over = 0, 0
                        elif wall(map_x-1, map_y):
                            over = 2, 0
                        else:
                            over = 3, 0
                        overlays[(map_x, map_y)] = tiles[over[0]][over[1]]
                else:
                    try:
                        tile = self.key[c]['tile'].split(',')
                        tile = int(tile[0]), int(tile[1])
                    except (ValueError, KeyError):
                        # Default to ground tile
                        tile = 0, 3
                tile_image = tiles[tile[0]][tile[1]]
                image.blit(tile_image,
                           (map_x*MAP_TILE_WIDTH, map_y*MAP_TILE_HEIGHT))
        return image, overlays

    def get_tile(self, x, y):
        """Tell what's at the specified position of the map."""

        try:
            char = self.map[y][x]
        except IndexError:
            return {}
        try:
            return self.key[char]
        except KeyError:
            return {}

    def get_bool(self, x, y, name):
        """Tell if the specified flag is set for position on the map."""

        value = self.get_tile(x, y).get(name)
        return value in (True, 1, 'true', 'yes', 'True', 'Yes', '1', 'on', 'On')

    def is_wall(self, x, y):
        """Is there a wall?"""

        return self.get_bool(x, y, 'wall')

    def is_blocking(self, x, y):
        """Is this place blocking movement?"""

        if not 0 <= x < self.width or not 0 <= y < self.height:
            return True
        return self.get_bool(x, y, 'block')


class Game(object):
    """The main game object."""

    def __init__(self):
        self.screen = pygame.display.get_surface()
        self.pressed_key = None
        self.game_over = False
        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.use_level(Level())
        self.map = self.level.map

    def use_level(self, level):
        """Set the level as the current one."""

        self.shadows = pygame.sprite.RenderUpdates()
        self.sprites = SortedUpdates()
        self.overlays = pygame.sprite.RenderUpdates()
        self.level = level
        #print(level.items)
        # Populate the game with the level's objects
        for pos, tile in level.items.items():
            
            if tile.get("player") in ('true', '1', 'yes', 'on'):
                sprite = Player(pos)
                self.player = sprite
            elif (tile["name"]=='house'):# here identify the specific house sprite
                sprite = Sprite(pos, SPRITE_CACHE[tile["sprite"]])
                self.house = sprite
            else: # here identify others sprites
                sprite = Sprite(pos, SPRITE_CACHE[tile["sprite"]])
            self.sprites.add(sprite) # here we add to the array of sprites
            self.shadows.add(Shadow(sprite))
        # Render the level map
        
        self.background, overlays = self.level.render()
        # Add the overlays for the level map
        for (x, y), image in overlays.items():
            overlay = pygame.sprite.Sprite(self.overlays)
            overlay.image = image
            overlay.rect = image.get_rect().move(x*24, y*16-16)

    def control(self, wpath=None):
        """Handle the controls of the game."""

        def walk(d):
            """Start walking in specified direction."""

            x, y = self.player.pos
            self.player.direction = d
            if not self.level.is_blocking(x+DX[d], y+DY[d]):
                self.player.animation = self.player.walk_animation()

        if wpath == None:
            keys = pygame.key.get_pressed()
        else:
            walk(wpath)
            return

        def pressed(key):
            """Check if the specified key is pressed."""

            return self.pressed_key == key or keys[key]

        if pressed(pg.K_UP): # UP:0 , DOWN:2 , LEFT:3 , RIGHT:1
            walk(0)
        elif pressed(pg.K_DOWN):
            walk(2)
        elif pressed(pg.K_LEFT):
            walk(3)
        elif pressed(pg.K_RIGHT):
            walk(1)
        elif pressed(pg.K_SPACE):

            self.walk_path = [ 0,1, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2 ]
            print("Space")
        self.pressed_key = None
    #here its a function to print the map, to make some proof
    def printMap(self):
        self.width = len(self.map[0])
        self.height = len(self.map)
        for y, line in enumerate(self.map):
            Wline = ""
            for x, c in enumerate(line):
                Wline = Wline + c
            print(Wline)
    def cleanPreviousHousePosition(self):
        newLine1 = ""
        # clean the previous house position in the map
        if(self.house.pos[0] == 0 and self.house.pos[1] == 0): # identify the first position
            newLine1 = '.'+ self.map[self.house.pos[1]][1:len(self.map[self.house.pos[1]])]
        elif(self.house.pos[0] == 14 and self.house.pos[1] == 14): #identify the last position
            newLine1 = self.map[self.house.pos[1]][0:len(self.map[self.house.pos[1]])-1]+'.'
        else:#in case of othe position
            newLine1 = self.map[self.house.pos[1]][0:self.house.pos[0]]+'.'+ self.map[self.house.pos[1]][self.house.pos[0]+1:len(self.map[self.house.pos[1]])]
        
        self.map[self.house.pos[1]]= newLine1

    def changeHousePos(self,xpos,ypos):
        newLine2 = ""

        # clean the previous house position in the map
        self.cleanPreviousHousePosition()

        # set the new house position in the map

        if(xpos == 0 and ypos == 0): # identify the first position
            newLine2 = 'h'+ self.map[ypos][1:len(self.map[ypos])]
        elif(xpos == 14 and ypos == 14): #identify the last position
            newLine2 = self.map[ypos][0:len(self.map[ypos])-1]+'h'
        else:#in case of othe position
            newLine2 = self.map[ypos][0:xpos]+'h'+ self.map[ypos][xpos+1:len(self.map[ypos])]
        
        self.map[ypos] = newLine2
        
        #asign to the sprite house the new position
        self.house.pos=(xpos,ypos)

    def main(self):
        """Run the main loop."""
        self.walk_path = []#[ 0,1, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2 ]
        clock = pygame.time.Clock()
        # Draw the whole screen initially
        self.screen.blit(self.background, (0, 0))
        self.overlays.draw(self.screen)
        pygame.display.flip()


        # clean the previous house position in the map
        self.cleanPreviousHousePosition()

        # Remove the Player character from the map
        xPlayer,yPlayer = self.player.pos[0],self.player.pos[1]
        newLine0=""
        #   print("player initPos: ",yPlayer ,xPlayer)
        if(xPlayer == 0 and yPlayer == 0): # identify the first position
            newLine0 = '.'+ self.map[yPlayer][1:len(self.map[yPlayer])]
        elif(xPlayer == 14 and yPlayer == 14): #identify the last position
            newLine0 = self.map[yPlayer][0:len(self.map[yPlayer])-1]+'.'
        else:#in case of othe position
            newLine0 = self.map[yPlayer][0:xPlayer]+'.'+ self.map[yPlayer][xPlayer+1:len(self.map[yPlayer])]
        
        self.map[yPlayer] = newLine0

        #Generate Graph map
        self.Graph = nx.Graph()
        linePos = []
        for y, line in enumerate(self.map):
            for x, c in enumerate(line):
                if(y < len(self.map)-1):# only ask for the previous of the last line
                    if(x < len(line)-1):# only ask for the previous of the last caracter
                        if(c == '.' and self.map[y][x+1] == '.'):# if the actual and the next position are floor
                            linePos.append(((x,y),(x+1,y),1))
                        if(c == '.' and self.map[y+1][x] == '.'):# if the actual and the bottom position are floor
                            linePos.append(((x,y),(x,y+1),1))
        self.Graph.add_weighted_edges_from(linePos)

        self.changeHousePos(self.house.pos[0],self.house.pos[1])

        # The main game loop
        while not self.game_over:
            # Don't clear shadows and overlays, only sprites.
            self.sprites.clear(self.screen, self.background)
            self.sprites.update()
            # If the player's animation is finished, check for keypresses
            if self.player.animation is None:
                self.control()
                if len(self.walk_path) > 0:
                    k = self.walk_path.pop(0)
                    #print(self.walk_path)
                    self.control(k)
                self.player.update()
            self.shadows.update()
            # Don't add shadows to dirty rectangles, as they already fit inside
            # sprite rectangles.
            self.shadows.draw(self.screen)
            dirty = self.sprites.draw(self.screen)
            # Don't add ovelays to dirty rectangles, only the places where
            # sprites are need to be updated, and those are already dirty.
            self.overlays.draw(self.screen)
            # Update the dirty areas of the screen
            pygame.display.update(dirty)
            # Wait for one tick of the game clock

            clock.tick(15)
            # Process pygame events
            for event in pygame.event.get():
                if event.type == pg.QUIT:
                    self.game_over = True
                elif event.type == pg.KEYDOWN:
                    self.pressed_key = event.key
                elif event.type == pg.MOUSEBUTTONDOWN:
                    x,y = pygame.mouse.get_pos()
                    # identify if the click area is inside the wold
                    if(not((x // MAP_TILE_WIDTH)>=15 or (y // MAP_TILE_HEIGHT)>=15)): 
                        xpos,ypos = (x // MAP_TILE_WIDTH), (y // MAP_TILE_HEIGHT)
                        if(self.map[ypos][xpos] == 'h'):
                            print("house")
                        elif(self.map[ypos][xpos] == 'X'):
                            print("wall")
                        elif(self.map[ypos][xpos] == 'b'):
                            print("crate")
                        elif(self.map[ypos][xpos] == '>'):
                            print("stairs")
                        elif(self.map[ypos][xpos] == '.'): # only could add house over floors
                            #print("floor")
                            #change the house position in the map to a new position
                            self.changeHousePos(xpos,ypos)
                            
                            if(not(self.player.pos[0]==self.house.pos[0] and self.player.pos[1]==self.house.pos[1])):
                                #print("player and house are not at the same position")
                                PlayerPos = ( self.player.pos[0] , self.player.pos[1] ) # player position
                                HousePos  = ( self.house.pos[0]  , self.house.pos[1]  ) # house position
                                NewPath = []
                                if(self.Graph.has_node(PlayerPos)):
                                    if(self.Graph.has_node(HousePos)):
                                        if(nx.has_path(self.Graph,PlayerPos,HousePos)):
                                            #print("Exist a path from Player Position to House Position")
                                            print(str(PlayerPos)+","+str(HousePos))
                                            NewPathPos = nx.dijkstra_path(self.Graph, PlayerPos, HousePos)
                                            #print(NewPathPos)
                                            NewPath=[]
                                            for i, pos in enumerate(NewPathPos):
                                                if(i<len(NewPathPos)-1):
                                                    PA = pos
                                                    PB = NewPathPos[i+1]
                                                    # UP:0 , DOWN:2 , LEFT:3 , RIGHT:1
                                                    if(  PA[0]+1 == PB[0] and PA[1]   == PB[1]): #RIGHT
                                                        NewPath.append(1)
                                                    elif(PA[0]-1 == PB[0] and PA[1]   == PB[1]): #LEFT
                                                        NewPath.append(3)
                                                    elif(PA[0]   == PB[0] and PA[1]-1 == PB[1]): #UP
                                                        NewPath.append(0)
                                                    elif(PA[0]   == PB[0] and PA[1]+1 == PB[1]): #DOWN
                                                        NewPath.append(2)
                                            self.walk_path = NewPath
                                            #print(NewPath)
                                            #self.printMap()
                                        else:
                                            print("No exist a path from Player Position to House Position")
                                    else:
                                        print("House position Node Doesnt exist")
                                else:
                                    print("Player position Node Doesnt exist")
                            #self.printMap()
                            #print("\n")
                        elif(self.map[ypos][xpos] == 's'):
                            print("skeleton")
                        
                        """
                        # mouse doesnt click over a wall
                        if(not(self.level.get_bool((x // MAP_TILE_WIDTH), (y // MAP_TILE_HEIGHT), 'wall'))):
                            dx = ((x // MAP_TILE_WIDTH) - self.house.pos[0]) * MAP_TILE_WIDTH
                            dy = ((y // MAP_TILE_HEIGHT) - self.house.pos[1]) * MAP_TILE_HEIGHT
                            self.house.move(dx, dy)
                        """
                #solve algorithm

if __name__ == "__main__":
    
    SPRITE_CACHE = TileCache()
    MAP_CACHE = TileCache(MAP_TILE_WIDTH, MAP_TILE_HEIGHT)
    TILE_CACHE = TileCache(32, 32)
    pygame.init()
    pygame.display.set_mode((424, 250))#424, 320
    Game().main()
