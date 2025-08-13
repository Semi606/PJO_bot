import random

# Список луту за категоріями та рідкістю
LOOT_ITEMS = {
    "hunt": {
        "Common": [
            {'id': 'monster_tooth', 'name': 'Зуб монстра', 'value': 2, 'lore': 'Звичайний зуб, що випав з гідри.', 'rarity': 'Common'},
            {'id': 'spool_of_thread', 'name': 'Моток ниток', 'value': 1, 'lore': 'Нитки, які, можливо, належали Мойрам.', 'rarity': 'Common'},
            {'id': 'wooden_sword', 'name': 'Дерев\'яний меч', 'value': 10, 'lore': 'З ним виглядаєш грізно, але краще не битися.', 'rarity': 'Common', 'type': 'weapon', 'strength_bonus': 2},
        ],
        "Rare": [
            {'id': 'harpy_feather', 'name': 'Перо гарпії', 'value': 15, 'lore': 'Гарно виглядає на капелюсі.', 'rarity': 'Rare'},
            {'id': 'drachma_bag', 'name': 'Мішечок з драхмами', 'value': 5, 'lore': 'У ньому додаткові драхми!', 'rarity': 'Rare'},
            {'id': 'small_potion', 'name': 'Мале зілля відновлення', 'value': 10, 'lore': '+5 енергії.', 'rarity': 'Rare'}
        ],
        "Epic": [
            {'id': 'recipe_blue_cookies', 'name': 'Рецепт синього печива', 'value': 50, 'lore': 'Оригінальний рецепт Саллі Джексон!', 'rarity': 'Epic'},
            {'id': 'medium_potion', 'name': 'Середнє зілля відновлення', 'value': 30, 'lore': '+10 енергії.', 'rarity': 'Epic'},
            {'id': 'big_potion', 'name': 'Велике зілля відновлення', 'value': 60, 'lore': '+15 енергії.', 'rarity': 'Epic'}
        ]
    },
    "fish": {
        "Common": [
            {'id': 'old_boot', 'name': 'Старий черевик', 'value': 1, 'lore': 'Хтось його точно загубив...', 'rarity': 'Common'},
            {'id': 'seaweed', 'name': 'Морські водорості', 'value': 1, 'lore': 'Пахнуть як хатинка Посейдона.', 'rarity': 'Common'}
        ],
        "Rare": [
            {'id': 'trident_shard', 'name': 'Уламок тризубця', 'value': 20, 'lore': 'Можливо, належить якомусь водному божеству.', 'rarity': 'Rare'},
            {'id': 'golden_drachma', 'name': 'Золота драхма', 'value': 10, 'lore': 'Сяє, як сонце!', 'rarity': 'Rare'},
            {'id': 'small_potion', 'name': 'Мале зілля відновлення', 'value': 10, 'lore': '+5 енергії.', 'rarity': 'Rare'}
        ],
        "Epic": [
            {'id': 'scallop_of_aphrodite', 'name': 'Мушля Афродіти', 'value': 60, 'lore': 'Мушля з таємницею, що може допомогти у вирішенні питань з любов\'ю.', 'rarity': 'Epic'},
            {'id': 'medium_potion', 'name': 'Середнє зілля відновлення', 'value': 30, 'lore': '+10 енергії.', 'rarity': 'Epic'},
            {'id': 'big_potion', 'name': 'Велике зілля відновлення', 'value': 60, 'lore': '+15 енергії.', 'rarity': 'Epic'}
        ]
    }
}

def get_random_loot(activity_type):
    loot_table = LOOT_ITEMS.get(activity_type)
    if not loot_table:
        return None
    
    rarities = ['Common', 'Rare', 'Epic']
    weights = [0.75, 0.2, 0.05]
    
    chosen_rarity = random.choices(rarities, weights=weights, k=1)[0]
    
    if chosen_rarity in loot_table and loot_table[chosen_rarity]:
        return random.choice(loot_table[chosen_rarity])
    else:
        return None

def get_item_info(item_id):
    for activity in LOOT_ITEMS.values():
        for rarity in activity.values():
            for item in rarity:
                if item['id'].strip() == item_id.strip():
                    return item
    return None