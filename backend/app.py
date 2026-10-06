from flask import Flask, jsonify, request
from flask_cors import CORS
import database as db

app = Flask(__name__)
CORS(app)  # разрешаем запросы с GitHub Pages


# ============================================================
# API: спектакли
# ============================================================

@app.route("/api/plays", methods=["GET"])
def api_get_plays():
    """Список всех спектаклей."""
    plays = db.get_all_plays()
    return jsonify(plays)


@app.route("/api/plays/<int:play_id>", methods=["GET"])
def api_get_play(play_id):
    """Один спектакль по ID."""
    play = db.get_play(play_id)
    if not play:
        return jsonify({"error": "Спектакль не найден"}), 404
    return jsonify(play)


@app.route("/api/plays/<int:play_id>/seats", methods=["GET"])
def api_get_seats(play_id):
    """Занятые места для спектакля."""
    play = db.get_play(play_id)
    if not play:
        return jsonify({"error": "Спектакль не найден"}), 404
    return jsonify({
        "play_id": play_id,
        "seats_total": play["seats_total"],
        "seats_taken": db.get_taken_seats(play_id)
    })


@app.route("/api/plays", methods=["POST"])
def api_add_play():
    """Добавить спектакль (админка)."""
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    date = data.get("date")
    price = data.get("price")
    seats_total = data.get("seats_total")

    if not title or not date or price is None or seats_total is None:
        return jsonify({"error": "Заполните все поля"}), 400
    if price < 0 or seats_total < 1:
        return jsonify({"error": "Некорректные цена или количество мест"}), 400

    new_id = db.add_play(title, date, price, seats_total)
    return jsonify({"id": new_id, "message": "Спектакль добавлен"}), 201


@app.route("/api/plays/<int:play_id>", methods=["DELETE"])
def api_delete_play(play_id):
    """Удалить спектакль."""
    play = db.get_play(play_id)
    if not play:
        return jsonify({"error": "Спектакль не найден"}), 404
    db.delete_play(play_id)
    return jsonify({"message": "Спектакль удалён"})


# ============================================================
# API: покупка билетов
# ============================================================

@app.route("/api/buy", methods=["POST"])
def api_buy():
    """Покупка билетов."""
    data = request.get_json() or {}
    play_id = data.get("play_id")
    seats = data.get("seats")
    order_number = data.get("order_number")

    if not play_id or not seats or not order_number:
        return jsonify({"error": "Не хватает данных"}), 400
    if not isinstance(seats, list) or not seats:
        return jsonify({"error": "Список мест пуст"}), 400

    success, message = db.buy_tickets(play_id, seats, order_number)
    if not success:
        return jsonify({"error": message}), 409

    return jsonify({"message": message, "order_number": order_number}), 201


# ============================================================
# Проверка работы сервера
# ============================================================

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "message": "Сервер работает"})

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "API театра работает",
        "endpoints": [
            "/api/health",
            "/api/plays",
            "/api/plays/<id>",
            "/api/plays/<id>/seats",
            "POST /api/plays",
            "DELETE /api/plays/<id>",
            "POST /api/buy"
        ]
    })


if __name__ == "__main__":
    # Инициализация БД при первом запуске
    db.init_db()
    db.seed_db()
    print("🚀 Сервер запущен: http://localhost:5000")
    app.run(debug=True, port=5000, host="0.0.0.0")

