
def dijkstra(graph, start, end):

    if start not in graph:
        raise ValueError(f"Centrale de départ inconnue dans le graphe : {start}")
    if end not in graph:
        raise ValueError(f"Centrale d'arrivée inconnue dans le graphe : {end}")

    # distances connues depuis start
    distances = {node: float("inf") for node in graph}
    distances[start] = 0

    previous = {}

    visited = set()

    while len(visited) < len(graph):
        current = None
        current_distance = float("inf")
        for node, dist in distances.items():
            if node not in visited and dist < current_distance:
                current = node
                current_distance = dist

        # rien d'accessible : on arrête
        if current is None:
            break

        if current == end:
            break

        visited.add(current)

        for edge in graph[current]:
            if not edge["available"]:
                continue

            neighbor = edge["to"]
            weight = edge["distance_km"]
            new_distance = current_distance + weight

            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                previous[neighbor] = current

    if distances[end] == float("inf"):
        return None, None

    path = [end]
    node = end
    while node != start:
        node = previous[node]
        path.append(node)
    path.reverse()

    return path, distances[end]





def shortest_paths_from(graph, start):
    if start not in graph:
        raise ValueError(f"Centrale de départ inconnue dans le graphe : {start}")

    distances = {node: float("inf") for node in graph}
    distances[start] = 0
    losses = {node: 0.0 for node in graph}
    previous = {}
    visited = set()

    while len(visited) < len(graph):
        current = None
        current_distance = float("inf")
        for node, dist in distances.items():
            if node not in visited and dist < current_distance:
                current = node
                current_distance = dist

        if current is None:
            break

        visited.add(current)

        for edge in graph[current]:
            if not edge["available"]:
                continue

            neighbor = edge["to"]
            new_distance = current_distance + edge["distance_km"]

            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                losses[neighbor] = losses[current] + edge["loss_percent"]
                previous[neighbor] = current

    results = {}
    for node in graph:
        if node == start or distances[node] == float("inf"):
            continue

        path = [node]
        current = node
        while current != start:
            current = previous[current]
            path.append(current)
        path.reverse()

        results[node] = {
            "path": path,
            "distance_km": distances[node],
            "loss_percent": losses[node],
        }

    return results

if __name__ == "__main__":
    from graph_loader import load_data, build_graph

    data = load_data()
    graph = build_graph(data)

    path, total_distance = dijkstra(graph, "golfech", "nogent")
    print("Chemin golfech -> nogent :", path)
    print("Distance totale (km) :", total_distance)

    mini_graph = {"a": [], "b": []}
    path, total_distance = dijkstra(mini_graph, "a", "b")
    print("Chemin a -> b (mini-graphe sans liaison) :", path)

    all_from_golfech = shortest_paths_from(graph, "golfech")
    print("Nombre de centrales atteignables depuis golfech :", len(all_from_golfech))
    print("Détail pour nogent :", all_from_golfech["nogent"])