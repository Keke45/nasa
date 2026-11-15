package astronauts

import (
	"database/sql"
	"net/http"
)

func AstronautsCollectionHandler(db *sql.DB) http.HandlerFunc {
	getHandler := ListAstronautsHandler(db)
	postHandler := RegistrationHandler(db)

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