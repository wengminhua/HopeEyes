
def find_object_from_cache(object_code):
    global g_result_cache_lock, g_result_cache
    if g_result_cache_lock.acquire():
        for num in range(len(g_result_cache)):
            detect_result = g_result_cache[len(g_result_cache) - num - 1]
            for detect_obj in detect_result:
                if detect_obj['category'] == object_code:
                    pos_x = detect_obj['position']['x']
                    image_width = 720
                    if pos_x <= (image_width / 3):
                        g_result_cache_lock.release()
                        return 'left'
                    if pos_x <= (image_width * 2 / 3):
                        g_result_cache_lock.release()
                        return 'middle'
                    g_result_cache_lock.release()
                    return 'right'
        g_result_cache_lock.release()
        return ''


def detect_moving_object_from_cache():
    global g_result_cache_lock, g_result_cache
    if g_result_cache_lock.acquire():
        # Clear result cache
        g_result_cache = []
        g_result_cache_lock.release()
    total_try_seconds = 20
    try_seconds = 2
    while total_try_seconds > 0:
        time.sleep(try_seconds)
        total_try_seconds -= try_seconds
        if g_result_cache_lock.acquire():
            object_move_ranges = []
            for index in range(len(g_result_cache)):
                result = g_result_cache[index]
                for r_index in range(len(result)):
                    item = result[r_index]
                    found = False
                    for m_index in range(len(object_move_ranges)):
                        if object_move_ranges[m_index]['category'] == item['category']:
                            x = item['position']['x']
                            y = item['position']['y']
                            start_x = object_move_ranges[m_index]['start_x']
                            start_y = object_move_ranges[m_index]['start_y']
                            position_change = int(math.sqrt(math.pow((x - start_x), 2) + math.pow((y - start_y), 2)))
                            start_size = object_move_ranges[m_index]['start_size']
                            size = item['position']['width'] * item['position']['height']
                            size_change = abs(size - start_size)
                            if position_change > object_move_ranges[m_index]['max_position_change']:
                                object_move_ranges[m_index]['max_position_change'] = position_change
                            if size_change > object_move_ranges[m_index]['max_size_change']:
                                object_move_ranges[m_index]['max_size_change'] = size_change
                            found = True
                    if not found:
                        object_move_ranges.append({
                            'category': item['category'],
                            'start_x': item['position']['x'],
                            'start_y': item['position']['y'],
                            'start_size': item['position']['width'] * item['position']['height'],
                            'max_position_change': 0,
                            'max_size_change': 0
                        })
            # Sort
            object_move_ranges.sort(moving_compare)
            g_result_cache_lock.release()
            print object_move_ranges
            # Filter max
            if object_move_ranges[0]['max_position_change'] >= 50 or object_move_ranges[0]['max_size_change'] >= (50 * 50):
                return object_move_ranges[0]['category']
    return ''


def moving_compare(objA, objB):
    position_weight = 0.7
    size_weight = 0.3
    a = objA['max_position_change'] * position_weight + objA['max_size_change'] * size_weight
    b = objB['max_position_change'] * position_weight + objB['max_size_change'] * size_weight
    if a >= b:
        return 1
    return -1

def get_object_name(object_code):
    with open('objects.json') as objects_file:
        objects = json.load(objects_file)
    for index in range(len(objects)):
        print object_code + '/' + objects[index - 1]['code']
        if objects[index - 1]['code'] == object_code:
            return objects[index - 1]['keyword']
    return ''


@g_app.route('/api/objects', methods=['GET'])
def get_objects():
    with open('objects.json') as objects_file:
        objects = json.load(objects_file)
    return jsonify(objects)


@g_app.route('/api/objects/find/<code>', methods=['GET'])
def find_object(code):
    object_name = get_object_name(code)
    print object_name
    if object_name == '':
        find_result_speaking = u'无法识别的物品'
    else:
        find_result = find_object_from_cache(code)
        find_result_speaking = ''
        if find_result == 'left':
            find_result_speaking = object_name + u'在您左前方'
        if find_result == 'middle':
            find_result_speaking = object_name + u'在您正前方'
        if find_result == 'right':
            find_result_speaking = object_name + u'在您右前方'
    return jsonify([{
        'result': find_result_speaking
    }])


@g_app.route('/api/objects/detect', methods=['GET'])
def detect_object():
    object_code = detect_moving_object_from_cache()
    print object_code
    if object_code == '':
        find_result_speaking = u'没有检测到物品'
    else:
        object_name = get_object_name(object_code)
        find_result_speaking = u'这是' + object_name
    return jsonify([{
        'result': find_result_speaking
    }])
