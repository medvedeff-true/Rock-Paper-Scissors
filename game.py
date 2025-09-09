# Powered by Medvedeff

import pygame  # импортируем pygame для работы с окном, событиями, графикой
import random  # импортируем random для генерации случайных позиций и направлений
import math    # импортируем math для векторной математики и проверки столкновений
import sys     # импортируем sys для корректного выхода из приложения
from typing import Tuple, List  # для типизации (удобно в комментариях и читабельности)

# -----------------------------
# Константы приложения
# -----------------------------
WIDTH, HEIGHT = 800, 800  # ширина и высота окна в пикселях
HUD_HEIGHT = 48  # высота верхней панели (где счётчики)
FPS = 60                  # целевой FPS для плавной анимации

# Стейты (состояния) экрана
STATE_MENU = "menu"         # состояние: меню ввода стартовых количеств и кнопка "Старт"
STATE_RUNNING = "running"   # состояние: идёт симуляция
STATE_FINISHED = "finished" # состояние: симуляция завершена, показ победителя и кнопки "Начать заново"

# Типы сущностей (игровых объектов)
TYPE_ROCK = "Камень"        # тип: камень
TYPE_SCISSORS = "Ножницы"   # тип: ножницы
TYPE_PAPER = "Бумага"       # тип: бумага

# Цвета для удобства (RGB)
COLOR_BG = (255, 255, 255)          # белый фон сцены
COLOR_PANEL = (230, 230, 230)       # светло-серый фон панелей/кнопок
COLOR_TEXT = (0, 0, 0)              # чёрный основной текст
COLOR_TEXT_DIM = (50, 50, 50)       # тёмно-серый текст (для подсказок)
COLOR_ACCENT = (90, 200, 250)      # акцент для рамок/кнопок
COLOR_ERROR = (255, 90, 90)        # цвет ошибок (например, валидация)

# Цвета объектов по типам
COLOR_ROCK = (160, 160, 160)       # серый для камня
COLOR_SCISSORS = (255, 160, 0)     # оранжевый для ножниц
COLOR_PAPER = (120, 200, 255)      # голубой для бумаги

# Радиус «тела» объектов (все одинаковые для упрощения)
ENTITY_RADIUS = 16  # пиксели

# Максимальная начальная скорость (вектор скорость будет внутри [-SPEED_MAX, +SPEED_MAX])
SPEED_MAX = 3.5  # пиксели/кадр

MIN_SPEED = 1.2           # минимальная допустимая скорость (помогает не «умирать» объектам)
SPEED_JITTER = 0.35       # небольшой случайный пинок при касаниях, чтобы не залипали
STUCK_FRAMES = 90         # через сколько кадров с очень низкой скоростью считаем объект «застрявшим»

# Кулдаун столкновения: после столкновения дадим объектам "передышку", чтобы они не перекипали мгновенно
COLLISION_COOLDOWN_FRAMES = 6  # количество кадров, пока объект не участвует в новых трансформациях

# Шрифт по умолчанию (pygame.freetype можно, но используем стандартный pygame.font)
pygame.init()  # инициализируем pygame
pygame.font.init()  # инициализируем модуль шрифтов

FONT_MAIN = pygame.font.SysFont("arial", 22)    # основной шрифт среднего размера
FONT_BIG = pygame.font.SysFont("arial", 32)     # шрифт покрупнее для заголовков
FONT_HUGE = pygame.font.SysFont("arial", 48)    # большой шрифт для итогового сообщения

# -----------------------------
# Класс кнопки Button
# -----------------------------
class Button:
    def __init__(self, rect: pygame.Rect, text: str, on_click=None):
        # rect: прямоугольник кнопки
        self.rect = rect
        # text: надпись на кнопке
        self.text = text
        # on_click: колбэк-функция, которую вызвать при клике
        self.on_click = on_click
        # hovered: флаг наведения курсора (для эффекта)
        self.hovered = False
        # clicked: фиксируем факт клика (для диалогов)
        self.clicked = False

    def handle_event(self, event: pygame.event.EventType):
        # Обработка события мыши для кнопки
        if event.type == pygame.MOUSEMOTION:
            # Проверяем, находится ли курсор над кнопкой
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.clicked = True
                if self.on_click:
                    self.on_click()

    def draw(self, surface: pygame.Surface):
        # Рисуем фон кнопки, меняя яркость при наведении
        base_color = COLOR_PANEL
        if self.hovered:
            base_color = (min(255, base_color[0] + 15),
                          min(255, base_color[1] + 15),
                          min(255, base_color[2] + 15))
        pygame.draw.rect(surface, base_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_ACCENT, self.rect, width=2, border_radius=8)
        text_surf = FONT_MAIN.render(self.text, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

# -----------------------------
# Класс поля ввода с кнопками +/- StepperInputBox
# -----------------------------
class StepperInputBox:
    def __init__(self, x: int, y: int, initial: str = "50"):
        self.rect = pygame.Rect(x, y, 140, 40)
        self.btn_minus = Button(pygame.Rect(x - 45, y, 40, 40), "-", self.decrement)
        self.btn_plus = Button(pygame.Rect(x + 145, y, 40, 40), "+", self.increment)
        self.text = initial
        self.active = False
        self.valid = True
        self.max_len = 5
        self.cursor_visible = True
        self.cursor_timer = 0

    def increment(self):
        val = self.get_value()
        if val < 1000:
            self.text = str(val + 1)

    def decrement(self):
        val = self.get_value()
        if val > 0:
            self.text = str(val - 1)

    def handle_event(self, event: pygame.event.EventType):
        self.btn_minus.handle_event(event)
        self.btn_plus.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            if self.active:
                self.cursor_timer = 0
                self.cursor_visible = True
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif event.unicode.isdigit():
                if len(self.text) < self.max_len:
                    self.text += event.unicode
            self.valid = self.is_valid_number()

    def is_valid_number(self) -> bool:
        if self.text == "":
            return False
        try:
            n = int(self.text)
            return 0 <= n <= 1000
        except ValueError:
            return False

    def get_value(self) -> int:
        try:
            return int(self.text)
        except ValueError:
            return 0

    def draw(self, surface: pygame.Surface):
        self.btn_minus.draw(surface)
        self.btn_plus.draw(surface)
        bg = COLOR_PANEL
        if self.active:
            bg = (min(255, bg[0] + 10), min(255, bg[1] + 10), min(255, bg[2] + 10))
        pygame.draw.rect(surface, bg, self.rect, border_radius=6)
        border_color = COLOR_ACCENT if self.valid else COLOR_ERROR
        pygame.draw.rect(surface, border_color, self.rect, width=2, border_radius=6)
        txt = self.text if self.text != "" else "0"
        text_surf = FONT_MAIN.render(txt, True, COLOR_TEXT)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

        # Курсор (чёрная полоска)
        if self.active:
            self.cursor_timer += 1
            if self.cursor_timer >= 30:  # мигание раз в полсекунды (при FPS=60)
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = 0
            if self.cursor_visible:
                cursor_x = text_rect.right + 3
                cursor_y1 = text_rect.top + 4
                cursor_y2 = text_rect.bottom - 4
                pygame.draw.line(surface, (0, 0, 0), (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)

# -----------------------------
# Класс сущности (летающий объект)
# -----------------------------
class Entity:
    def __init__(self, typ: str, pos: Tuple[float, float], vel: Tuple[float, float]):
        self.typ = typ
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.r = ENTITY_RADIUS
        self.collision_cooldown = 0
        self.slow_frames = 0
        self.enforce_speed()

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.x - self.r < 0:
            self.x = self.r
            self.vx = -self.vx
        elif self.x + self.r > WIDTH:
            self.x = WIDTH - self.r
            self.vx = -self.vx
        if self.y - self.r < HUD_HEIGHT:
            self.y = HUD_HEIGHT + self.r
            self.vy = -self.vy
        elif self.y + self.r > HEIGHT:
            self.y = HEIGHT - self.r
            self.vy = -self.vy
        self.enforce_speed()
        if self.collision_cooldown > 0:
            self.collision_cooldown -= 1

    def draw(self, surface: pygame.Surface):
        if self.typ == TYPE_ROCK:
            img = IMG_ROCK
            border_color = (120, 120, 120)
        elif self.typ == TYPE_SCISSORS:
            img = IMG_SCISSORS
            border_color = (80, 180, 255)
        else:
            img = IMG_PAPER
            border_color = (255, 200, 60)
        pygame.draw.circle(surface, border_color, (int(self.x), int(self.y)), self.r + 3)
        rect = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(img, rect)

    def enforce_speed(self):
        vx, vy = self.vx, self.vy
        speed = math.hypot(vx, vy)
        if speed < MIN_SPEED * 0.75:
            self.slow_frames += 1
        else:
            self.slow_frames = max(0, self.slow_frames - 1)
        if self.slow_frames >= STUCK_FRAMES:
            self.vx, self.vy = random_velocity()
            self.slow_frames = 0
            return
        if speed < MIN_SPEED:
            if speed == 0:
                self.vx, self.vy = random_velocity()
            else:
                k = MIN_SPEED / speed
                self.vx *= k
                self.vy *= k
        elif speed > SPEED_MAX:
            k = SPEED_MAX / speed
            self.vx *= k
            self.vy *= k

# -----------------------------
# Логика "кто кого бьёт"
# -----------------------------
def winner_of(a: str, b: str) -> str:
    if a == b:
        return ""
    if a == TYPE_ROCK and b == TYPE_SCISSORS:
        return a
    if b == TYPE_ROCK and a == TYPE_SCISSORS:
        return b
    if a == TYPE_SCISSORS and b == TYPE_PAPER:
        return a
    if b == TYPE_SCISSORS and a == TYPE_PAPER:
        return b
    if a == TYPE_PAPER and b == TYPE_ROCK:
        return a
    if b == TYPE_PAPER and a == TYPE_ROCK:
        return b
    return ""

# -----------------------------
# Функция генерации случайной скорости
# -----------------------------
def random_velocity() -> Tuple[float, float]:
    vx = random.uniform(-SPEED_MAX, SPEED_MAX)
    vy = random.uniform(-SPEED_MAX, SPEED_MAX)
    if abs(vx) < MIN_SPEED:
        vx = MIN_SPEED if vx >= 0 else -MIN_SPEED
    if abs(vy) < MIN_SPEED:
        vy = MIN_SPEED if vy >= 0 else -MIN_SPEED
    return vx, vy

# -----------------------------
# Функция генерации стартового набора сущностей
# -----------------------------
def spawn_entities(n_rock: int, n_scissors: int, n_paper: int) -> List[Entity]:
    entities: List[Entity] = []
    def add_many(typ: str, count: int):
        for _ in range(count):
            x = random.uniform(ENTITY_RADIUS + 2, WIDTH - ENTITY_RADIUS - 2)
            y = random.uniform(HUD_HEIGHT + ENTITY_RADIUS + 2, HEIGHT - ENTITY_RADIUS - 2)
            vx, vy = random_velocity()
            entities.append(Entity(typ, (x, y), (vx, vy)))
    add_many(TYPE_ROCK, n_rock)
    add_many(TYPE_SCISSORS, n_scissors)
    add_many(TYPE_PAPER, n_paper)
    return entities

# -----------------------------
# Столкновения: обработка преобразований
# -----------------------------
def process_collisions(entities: List[Entity]):
    n = len(entities)
    for i in range(n):
        a = entities[i]
        for j in range(i + 1, n):
            b = entities[j]
            if a.collision_cooldown > 0 or b.collision_cooldown > 0:
                continue
            dx = a.x - b.x
            dy = a.y - b.y
            dist_sq = dx * dx + dy * dy
            min_dist = a.r + b.r
            if dist_sq <= min_dist * min_dist:
                w = winner_of(a.typ, b.typ)
                if w == "":
                    separate(a, b)
                    continue
                if w == a.typ and b.typ != a.typ:
                    b.typ = a.typ
                    a.collision_cooldown = COLLISION_COOLDOWN_FRAMES
                    b.collision_cooldown = COLLISION_COOLDOWN_FRAMES
                elif w == b.typ and a.typ != b.typ:
                    a.typ = b.typ
                    a.collision_cooldown = COLLISION_COOLDOWN_FRAMES
                    b.collision_cooldown = COLLISION_COOLDOWN_FRAMES
                separate(a, b)

# -----------------------------
# Раздвижение объектов после столкновения
# -----------------------------
def separate(a: Entity, b: Entity):
    dx = a.x - b.x
    dy = a.y - b.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        angle = random.uniform(0, 2 * math.pi)
        dx = math.cos(angle)
        dy = math.sin(angle)
        dist = 1.0
    nx = dx / dist
    ny = dy / dist
    tx = -ny
    ty = nx
    target = a.r + b.r + 1.0
    penetration = target - dist
    if penetration > 0:
        a.x += nx * (penetration * 0.5)
        a.y += ny * (penetration * 0.5)
        b.x -= nx * (penetration * 0.5)
        b.y -= ny * (penetration * 0.5)
    va_n = a.vx * nx + a.vy * ny
    vb_n = b.vx * nx + b.vy * ny
    va_t = a.vx * tx + a.vy * ty
    vb_t = b.vx * tx + b.vy * ty
    a_vn_new = vb_n
    b_vn_new = va_n
    a.vx = a_vn_new * nx + va_t * tx
    a.vy = a_vn_new * ny + va_t * ty
    b.vx = b_vn_new * nx + vb_t * tx
    b.vy = b_vn_new * ny + vb_t * ty
    a.vx += random.uniform(-SPEED_JITTER, SPEED_JITTER)
    a.vy += random.uniform(-SPEED_JITTER, SPEED_JITTER)
    b.vx += random.uniform(-SPEED_JITTER, SPEED_JITTER)
    b.vy += random.uniform(-SPEED_JITTER, SPEED_JITTER)
    a.enforce_speed()
    b.enforce_speed()

# -----------------------------
# Проверка — остался ли один тип
# -----------------------------
def check_winner(entities: List[Entity]) -> str:
    types_present = set(e.typ for e in entities)
    if not types_present:
        return ""
    if len(types_present) == 1:
        return types_present.pop()
    return ""

# -----------------------------
# Функция отрисовки шапки/панели состояния
# -----------------------------
def draw_hud(surface: pygame.Surface, entities: List[Entity]):
    # Рисуем полоску сверху для текущей статистики
    panel_rect = pygame.Rect(0, 0, WIDTH, 48)
    pygame.draw.rect(surface, COLOR_PANEL, panel_rect)
    pygame.draw.line(surface, (50, 55, 60), (0, panel_rect.bottom), (WIDTH, panel_rect.bottom), 2)
    # Считаем количество каждого типа
    cnt_rock = sum(1 for e in entities if e.typ == TYPE_ROCK)
    cnt_scissors = sum(1 for e in entities if e.typ == TYPE_SCISSORS)
    cnt_paper = sum(1 for e in entities if e.typ == TYPE_PAPER)
    # Готовим текст
    text = f"Камней: {cnt_rock}   |   Ножниц: {cnt_scissors}   |   Бумаги: {cnt_paper}"
    txt_surf = FONT_MAIN.render(text, True, COLOR_TEXT)
    txt_rect = txt_surf.get_rect(midleft=(14, panel_rect.centery))
    surface.blit(txt_surf, txt_rect)


# -----------------------------
# Главная функция приложения
# -----------------------------
def main():
    exit_confirm = {"confirm": False}
    # Создаём окно фиксированного размера
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    exit_button = Button(pygame.Rect(WIDTH - 100, 5, 80, 30), "Выйти")

    global IMG_ROCK, IMG_SCISSORS, IMG_PAPER
    IMG_ROCK = pygame.transform.smoothscale(
        pygame.image.load("img/R.png").convert_alpha(), (ENTITY_RADIUS * 2, ENTITY_RADIUS * 2)
    )
    IMG_SCISSORS = pygame.transform.smoothscale(
        pygame.image.load("img/S.png").convert_alpha(), (ENTITY_RADIUS * 2, ENTITY_RADIUS * 2)
    )
    IMG_PAPER = pygame.transform.smoothscale(
        pygame.image.load("img/P.png").convert_alpha(), (ENTITY_RADIUS * 2, ENTITY_RADIUS * 2)
    )

    # Заголовок окна
    pygame.display.set_caption("Камень-Ножницы-Бумага")
    # Часы для контроля FPS
    clock = pygame.time.Clock()

    # Текущее состояние экрана — начнём с меню
    state = STATE_MENU

    # Поля ввода для меню
    input_rock = StepperInputBox(330, 230, initial="50")
    input_scissors = StepperInputBox(330, 310, initial="50")
    input_paper = StepperInputBox(330, 390, initial="50")

    # Текстовые подписи для полей ввода
    label_rock = "Сколько будет на старте: камней"
    label_scissors = "Сколько будет на старте: ножниц"
    label_paper = "Сколько будет на старте: бумаги"

    # Сообщение валидации (например, когда все нули)
    validation_message = ""

    # Список сущностей (создаём при старте симуляции)
    entities: List[Entity] = []

    # Имя победителя (строка типа TYPE_ROCK/SCISSORS/PAPER)
    winner_name = ""

    # Колбэк нажатия кнопки "Старт"
    def start_simulation():
        nonlocal state, entities, validation_message, winner_name
        n_r = input_rock.get_value()
        n_s = input_scissors.get_value()
        n_p = input_paper.get_value()
        input_rock.valid = input_rock.is_valid_number()
        input_scissors.valid = input_scissors.is_valid_number()
        input_paper.valid = input_paper.is_valid_number()
        if not (input_rock.valid and input_scissors.valid and input_paper.valid):
            validation_message = "Ошибка: проверьте правильность чисел (0..1000)."
            return
        if (n_r + n_s + n_p) == 0:
            validation_message = "Нужно указать хотя бы одно положительное количество."
            return
        entities = spawn_entities(n_r, n_s, n_p)
        winner_name = ""
        state = STATE_RUNNING

    # Кнопка "Старт"
    button_start = Button(pygame.Rect(300, 530, 200, 50), "Старт", start_simulation)

    # Колбэк нажатия "Начать заново"
    def restart():
        nonlocal state, validation_message, winner_name, entities
        state = STATE_MENU
        validation_message = ""
        winner_name = ""
        entities = []

    button_restart = Button(pygame.Rect(WIDTH // 2 - 110, HEIGHT // 2 + 60, 220, 50), "Начать заново", restart)

    def ask_exit():
        nonlocal state, entities, winner_name, validation_message
        exit_confirm["confirm"] = show_confirmation_dialog(screen, "Вернуться в меню?")
        if exit_confirm["confirm"]:
            state = STATE_MENU
            entities = []
            winner_name = ""
            validation_message = ""

    exit_button = Button(pygame.Rect(WIDTH - 100, 5, 80, 30), "Выйти", ask_exit)

    running = True

    while running:
        for event in pygame.event.get():
            exit_button.handle_event(event)

            if event.type == pygame.QUIT:
                running = False
                break

            if state == STATE_MENU:
                input_rock.handle_event(event)
                input_scissors.handle_event(event)
                input_paper.handle_event(event)
                button_start.handle_event(event)

            elif state == STATE_RUNNING:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            elif state == STATE_FINISHED:
                button_restart.handle_event(event)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

        screen.fill(COLOR_BG)

        if state == STATE_MENU:
            title = "Пусть победит сильнейший!"
            title_surf = FONT_BIG.render(title, True, COLOR_TEXT)
            title_rect = title_surf.get_rect(center=(WIDTH // 2, 120))
            screen.blit(title_surf, title_rect)

            lbl1 = FONT_MAIN.render(label_rock, True, COLOR_TEXT_DIM)
            screen.blit(lbl1, (WIDTH // 2 - 160, 200))
            input_rock.draw(screen)

            lbl2 = FONT_MAIN.render(label_scissors, True, COLOR_TEXT_DIM)
            screen.blit(lbl2, (WIDTH // 2 - 160, 280))
            input_scissors.draw(screen)

            lbl3 = FONT_MAIN.render(label_paper, True, COLOR_TEXT_DIM)
            screen.blit(lbl3, (WIDTH // 2 - 160, 360))
            input_paper.draw(screen)

            hint = "Подсказка: введите 0 - 1000 для каждого вида и нажмите 'Старт'"
            hint_surf = FONT_MAIN.render(hint, True, COLOR_TEXT_DIM)
            hint_rect = hint_surf.get_rect(center=(WIDTH // 2, 500))
            screen.blit(hint_surf, hint_rect)

            if validation_message:
                val_surf = FONT_MAIN.render(validation_message, True, COLOR_ERROR)
                val_rect = val_surf.get_rect(center=(WIDTH // 2, 540))
                screen.blit(val_surf, val_rect)

            button_start.draw(screen)

        elif state == STATE_RUNNING:
            draw_hud(screen, entities)
            exit_button.draw(screen)

            for e in entities:
                e.update()
                e.draw(screen)

            process_collisions(entities)

            winner_name = check_winner(entities)
            if winner_name:
                state = STATE_FINISHED

        elif state == STATE_FINISHED:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            screen.blit(overlay, (0, 0))

            msg = f"Победили: {winner_name}"
            msg_surf = FONT_HUGE.render(msg, True, (0, 0, 0))
            msg_rect = msg_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
            screen.blit(msg_surf, msg_rect)

            button_restart.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit(0)


def show_confirmation_dialog(surface, message: str) -> bool:
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    box_rect = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 80, 360, 160)
    pygame.draw.rect(surface, (245, 245, 245), box_rect, border_radius=12)
    pygame.draw.rect(surface, (80, 80, 80), box_rect, 2, border_radius=12)

    txt = FONT_MAIN.render(message, True, (0, 0, 0))
    txt_rect = txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
    surface.blit(txt, txt_rect)

    result = False
    btn_yes = Button(pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 20, 100, 36), "Да", lambda: setattr(sys.modules[__name__], "_dialog_result", True))
    btn_no = Button(pygame.Rect(WIDTH // 2 + 30, HEIGHT // 2 + 20, 100, 36), "Нет", lambda: setattr(sys.modules[__name__], "_dialog_result", False))

    pygame.display.flip()
    waiting = True
    global _dialog_result
    _dialog_result = None

    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            btn_yes.handle_event(event)
            btn_no.handle_event(event)

        if _dialog_result is not None:
            result = _dialog_result
            waiting = False

        btn_yes.draw(surface)
        btn_no.draw(surface)
        pygame.display.update()

    return result


if __name__ == "__main__":
    main()