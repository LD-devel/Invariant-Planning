;; Enrico Scala (enricos83@gmail.com)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; counters-ineq-rnd domain, functional strips version
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; This domain describes a set of counters that can be increased and decreased. The rate of such counter is however variable!

(define (domain fn-counters)
    ;(:requirements :strips :typing :equality :adl)
    (:types counter)

    (:functions
        (value ?c - counter);; - int  ;; The value shown in counter ?c
        (rate_value ?c - counter);;
        (max_int);; -  int ;; The maximum integer we consider - a static value
    )

    ;; Increment the value in the given counter by one
    (:action increment_a
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_b
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_c
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_d
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Decrement the value in the given counter by one
    (:action decrement_e
         :parameters (?c - counter)
         :precondition (and (>= (- (value ?c) (rate_value ?c)) 0))
         :effect (and (decrease (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_f
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_g
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_h
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Increment the value in the given counter by one
    (:action increment_i
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
   ;; Increment the value in the given counter by one
    (:action increment_j
         :parameters (?c - counter)
         :precondition (and (<= (+ (value ?c) (rate_value ?c)) (max_int)))
         :effect (and (increase (value ?c) (rate_value ?c)))
    )
    ;; Decrement the value in the given counter by one
    (:action decrement
         :parameters (?c - counter)
         :precondition (and (>= (- (value ?c) (rate_value ?c)) 0))
         :effect (and (decrease (value ?c) (rate_value ?c)))
    )


)
