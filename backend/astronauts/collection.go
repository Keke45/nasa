package astronauts

import (
	"database/sql"
	"net/http"

	"astronaut-health-intelligence/intelligence"
)

func AstronautsCollectionHandler(
	db *sql.DB,
	intelligenceClients ...*intelligence.Client,
) http.HandlerFunc {
	getHandler := ListAstronautsHandler(db)
	postHandler := RegistrationHandler(db, intelligenceClients...)

	return func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			getHandler(w, r)

		case http.MethodPost:
			postHandler(w, r)

		default:
			w.Header().Set("Allow", "GET, POST")
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	}
}
