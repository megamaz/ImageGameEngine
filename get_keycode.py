import pygame

pygame.init()
screen = pygame.display.set_mode((100, 100))
pygame.display.flip()

while True:
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            print(event.key, hex(event.key))
        
        if event.type == pygame.QUIT:
            quit()